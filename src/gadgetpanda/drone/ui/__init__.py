"""Web FPV remote for gadgetpanda.drone (FastAPI + WebSocket + RTSP→MJPEG)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from gadgetpanda.drone import Command, Drone, Stick, UnsupportedCapability, by_id
from gadgetpanda.drone.ffmpeg import resolve_ffmpeg
from gadgetpanda.drone.protocol import DEFAULT_RTSP

STATIC = Path(__file__).parent / "static"
log = logging.getLogger("gadgetpanda.drone.ui")


def _catalog(model: str = "flow") -> dict:
    profile = by_id(model)
    return {
        "type": "catalog",
        "model": profile.id,
        "display_name": profile.display_name,
        "sticks": [s.value for s in Stick],
        "commands": [c.value for c in Command],
        "rtsp": profile.endpoints.rtsp_url,
    }


def _rtsp_for_host(host: str | None, model: str) -> str:
    profile = by_id(model)
    if not host:
        return profile.endpoints.rtsp_url
    # Prefer craft IP that the UDP stack already uses.
    return f"rtsp://{host}:7070/webcam"


class DroneHub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.status = {
            "state": "idle",
            "name": "",
            "address": "",
            "model": "flow",
            "error": "",
            "demo": False,
            "rtsp": DEFAULT_RTSP,
            "stream": "/stream.mjpeg",
            "stream_error": "",
        }
        self.drone: Drone | None = None
        self._cmd_lock = asyncio.Lock()

    async def broadcast(self, message: dict) -> None:
        message.setdefault("t", time.time())
        dead: list[WebSocket] = []
        payload = json.dumps(message, ensure_ascii=False)
        for client in list(self.clients):
            try:
                await client.send_text(payload)
            except Exception:
                dead.append(client)
        for client in dead:
            self.clients.discard(client)

    async def welcome(self, socket: WebSocket) -> None:
        await socket.send_text(json.dumps({"type": "status", **self.status}, ensure_ascii=False))
        await socket.send_text(json.dumps(_catalog(self.status.get("model") or "flow"), ensure_ascii=False))

    async def set_status(self, **kwargs) -> None:
        self.status.update(kwargs)
        await self.broadcast({"type": "status", **self.status})

    async def attach(self, drone: Drone, *, demo: bool = False) -> None:
        self.drone = drone
        rtsp = _rtsp_for_host(drone.host if not demo else None, drone.profile.id)
        await self.set_status(
            state="connected",
            name=drone.name,
            address=drone.address,
            model=drone.profile.id,
            demo=demo,
            error="",
            rtsp=rtsp,
            stream="/stream.mjpeg",
        )

    async def handle(self, message: dict) -> None:
        if self.drone is None or not self.drone.connected:
            await self.broadcast({"type": "log", "text": "drone not connected"})
            return
        kind = message.get("type")
        # High-rate stick updates must not wait behind takeoff/land pulses.
        if kind == "axes":
            try:
                self.drone.set_axes(
                    roll=message.get("roll"),
                    pitch=message.get("pitch"),
                    throttle=message.get("throttle"),
                    yaw=message.get("yaw"),
                )
            except Exception as exc:
                await self.broadcast({"type": "log", "text": f"axes error: {exc}"})
            return

        async with self._cmd_lock:
            try:
                if kind == "hold_start":
                    await self.drone.stick(str(message.get("name") or "hover"))
                elif kind == "hold_stop":
                    await self.drone.hover()
                elif kind == "stick":
                    await self.drone.stick(str(message.get("name") or "hover"))
                elif kind == "command":
                    name = str(message.get("name") or "")
                    await self.drone.command(name)
                    await self.broadcast({"type": "log", "text": f"cmd {name}"})
                elif kind == "raw":
                    raw = str(message.get("hex") or "")
                    await self.drone.raw_write(raw)
                elif kind == "stop":
                    await self.drone.command("emergency")
                    await self.broadcast({"type": "log", "text": "emergency stop"})
                elif kind == "hover":
                    await self.drone.hover()
            except UnsupportedCapability as exc:
                await self.broadcast({"type": "log", "text": f"unsupported: {exc}"})
            except Exception as exc:
                await self.broadcast({"type": "log", "text": f"error: {exc}"})


hub = DroneHub()
app = FastAPI(title="Gadget Panda Drone")
if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC), name="assets")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


async def _mjpeg_frames(rtsp_url: str, *, transport: str = "tcp"):
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found — pip install 'gadgetpanda[ui]' (bundles imageio-ffmpeg)")
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-rtsp_transport",
        transport,
        "-i",
        rtsp_url,
        "-an",
        "-f",
        "mjpeg",
        "-q:v",
        "7",
        "-r",
        "15",
        "pipe:1",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None
    buf = b""
    got_frame = False
    try:
        while True:
            chunk = await proc.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            while True:
                start = buf.find(b"\xff\xd8")
                end = buf.find(b"\xff\xd9")
                if start < 0 or end < 0 or end < start:
                    if start > 0:
                        buf = buf[start:]
                    break
                frame = buf[start : end + 2]
                buf = buf[end + 2 :]
                got_frame = True
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(frame)).encode()
                    + b"\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
    finally:
        err = b""
        try:
            err = await asyncio.wait_for(proc.stderr.read(), timeout=0.2)
        except Exception:
            pass
        if proc.returncode is None:
            proc.kill()
            try:
                await proc.wait()
            except Exception:
                pass
        if not got_frame:
            detail = err.decode("utf-8", errors="replace").strip() or f"ffmpeg exit {proc.returncode}"
            raise RuntimeError(f"RTSP via {transport} failed: {detail}")


@app.get("/api/stream-info")
async def stream_info() -> JSONResponse:
    ffmpeg = resolve_ffmpeg()
    return JSONResponse(
        {
            "rtsp": hub.status.get("rtsp"),
            "stream": hub.status.get("stream"),
            "ffmpeg": bool(ffmpeg),
            "ffmpeg_path": ffmpeg,
            "demo": hub.status.get("demo"),
            "stream_error": hub.status.get("stream_error") or "",
        }
    )


@app.get("/stream.mjpeg")
async def stream_mjpeg():
    from gadgetpanda.license import require as require_license

    require_license("drone.rtsp")
    if hub.status.get("demo"):
        return JSONResponse({"error": "demo mode has no live RTSP"}, status_code=503)
    rtsp = str(hub.status.get("rtsp") or DEFAULT_RTSP)
    if not resolve_ffmpeg():
        return JSONResponse(
            {"error": "ffmpeg required for RTSP preview — pip install 'gadgetpanda[ui]'"},
            status_code=503,
        )

    async def gen():
        last_error = ""
        for transport in ("tcp", "udp"):
            try:
                async for part in _mjpeg_frames(rtsp, transport=transport):
                    if hub.status.get("stream_error"):
                        hub.status["stream_error"] = ""
                    yield part
                return
            except Exception as exc:
                last_error = str(exc)
                log.warning("mjpeg %s: %s", transport, exc)
        hub.status["stream_error"] = last_error
        await hub.broadcast({"type": "status", **hub.status})

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"},
    )


@app.websocket("/ws")
async def ws_endpoint(socket: WebSocket) -> None:
    await socket.accept()
    hub.clients.add(socket)
    await hub.welcome(socket)
    try:
        while True:
            raw = await socket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            await hub.handle(message)
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.discard(socket)


async def serve(
    host: str = "127.0.0.1",
    port: int = 8767,
    drone_host: str | None = None,
    timeout: float = 3.0,
    demo: bool = False,
    model: str = "flow",
) -> None:
    from gadgetpanda.license import require as require_license

    require_license("drone.ui")
    import uvicorn

    drone = Drone(drone_host, model=model, demo=demo)
    try:
        await drone.connect(timeout=timeout)
        await hub.attach(drone, demo=demo)
    except Exception as exc:
        await hub.set_status(
            state="error",
            error=str(exc),
            model=model,
            demo=demo,
            rtsp=_rtsp_for_host(drone_host, model),
        )
        if not demo:
            raise

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    try:
        await server.serve()
    finally:
        await drone.disconnect()
