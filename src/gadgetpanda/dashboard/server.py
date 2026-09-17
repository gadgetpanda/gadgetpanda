from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gadgetpanda.dashboard.payload import encode_event, encode_snapshot
from gadgetpanda.protocol import (
    CMD_GET_HEALTH,
    CMD_GET_SPORT,
    CMD_GET_TEMP,
    CMD_SET_SPO2,
    RX_RAW_STREAM,
    UUID_FITNESS_RX,
    pack,
)
from gadgetpanda.ring import Ring
from gadgetpanda.stream import DEFAULT_MODE, allows_event, mode_payload, resolve_mode
from gadgetpanda.testing import FakeBleClient, SimulatedRing

STATIC = Path(__file__).parent / "static"
log = logging.getLogger("gadgetpanda.ui")


class Hub:
    def __init__(self, mode: str = DEFAULT_MODE) -> None:
        self.clients: set[WebSocket] = set()
        self.status = {"state": "idle", "name": "", "address": "", "error": ""}
        self.latest: dict[str, dict] = {}
        self.mode = resolve_mode(mode).id
        self.ring: Ring | None = None
        self.firmware: SimulatedRing | None = None
        self._mode_lock = asyncio.Lock()

    async def broadcast(self, message: dict) -> None:
        kind = message.get("type")
        if kind and not allows_event(self.mode, kind):
            return
        message.setdefault("t", time.time())
        if kind:
            self.latest[kind] = message
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
        await socket.send_text(json.dumps(mode_payload(self.mode), ensure_ascii=False))
        for message in self.latest.values():
            if message.get("type") in {"status", "mode"}:
                continue
            if allows_event(self.mode, message.get("type", "")):
                await socket.send_text(json.dumps(message, ensure_ascii=False))

    async def set_user(self, message: dict) -> None:
        ring = self.ring
        if ring is None or not ring.connected:
            await self.broadcast({"type": "user_status", "ok": False, "error": "ยังไม่ต่อแหวน"})
            return
        try:
            age = _profile_int(message.get("age"), 1, 120, "อายุ")
            weight = _profile_int(message.get("weight_kg"), 20, 250, "น้ำหนัก")
            height = _profile_int(message.get("height_cm"), 80, 250, "ส่วนสูง")
            sex = message.get("sex")
            sex_value = None if sex in (None, "") else _profile_int(sex, 0, 1, "เพศ")
        except ValueError as exc:
            await self.broadcast({"type": "user_status", "ok": False, "error": str(exc)})
            return
        try:
            await ring.set_user(age, sex_value, weight, height)
            await ring.get_user()
            await self.broadcast({"type": "user_status", "ok": True, "error": ""})
        except Exception as exc:
            await self.broadcast({"type": "user_status", "ok": False, "error": str(exc)})

    async def set_mode(self, mode: str) -> None:
        spec = resolve_mode(mode)
        async with self._mode_lock:
            self.mode = spec.id
            ring = self.ring
            if ring is not None and ring.connected:
                await ring.apply_stream(spec.id)
        await self.broadcast(mode_payload(self.mode))

    def enqueue(self, queue: asyncio.Queue, event: str, *args, **_kwargs) -> None:
        try:
            encoded = encode_event(event, args[0] if args else None)
            if encoded is None or not allows_event(self.mode, encoded.get("type", "")):
                return
            try:
                queue.put_nowait(encoded)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                queue.put_nowait(encoded)
        except Exception:
            log.exception("dashboard enqueue failed for %s", event)

    async def drain(self, queue: asyncio.Queue, ring: Ring) -> None:
        while ring.connected:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=1.0)
                await self.broadcast(message)
            except asyncio.TimeoutError:
                continue

    async def run_ring(self, address: str | None, timeout: float) -> None:
        while True:
            try:
                await self._session(address, timeout)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.status = {
                    "state": "error",
                    "name": "",
                    "address": address or "",
                    "error": str(exc),
                }
                await self.broadcast({"type": "status", **self.status})
                log.exception("dashboard ring failed")
            await asyncio.sleep(4.0)

    async def _session(self, address: str | None, timeout: float) -> None:
        self.status = {"state": "connecting", "name": "", "address": address or "", "error": ""}
        await self.broadcast({"type": "status", **self.status})
        ring = Ring(address, name="RING503PANDA") if address else await Ring.find(timeout=timeout)
        queue: asyncio.Queue = asyncio.Queue(maxsize=400)
        ring.on("*", lambda event, *args, **kwargs: self.enqueue(queue, event, *args, **kwargs))
        self.ring = ring
        try:
            await ring.connect(timeout=max(20.0, timeout))
            self.status = {
                "state": "live",
                "name": ring.name,
                "address": ring.address,
                "error": "",
            }
            await self.broadcast({"type": "status", **self.status})
            await self.broadcast(mode_payload(self.mode))
            for message in encode_snapshot(ring):
                await self.broadcast(message)
            await ring.get_user()
            await ring.apply_stream(self.mode, interval=1.5)
            await self.drain(queue, ring)
            self.status = {
                "state": "disconnected",
                "name": ring.name,
                "address": ring.address,
                "error": "แหวนหลุดการเชื่อมต่อ",
            }
            await self.broadcast({"type": "status", **self.status})
        finally:
            self.ring = None
            try:
                await ring.stop_realtime()
            except Exception:
                pass
            try:
                await ring.disconnect()
            except Exception:
                pass

    async def run_demo(self) -> None:
        firmware = SimulatedRing(name="RING503PANDA-DEMO")
        ring = Ring(firmware.advertised(), transport=FakeBleClient(firmware))
        queue: asyncio.Queue = asyncio.Queue(maxsize=400)
        ring.on("*", lambda event, *args, **kwargs: self.enqueue(queue, event, *args, **kwargs))
        self.ring = ring
        self.firmware = firmware
        self.status = {
            "state": "demo",
            "name": "RING503PANDA-DEMO",
            "address": firmware.address,
            "error": "",
        }
        await self.broadcast({"type": "status", **self.status})
        await self.broadcast(mode_payload(self.mode))
        await ring.connect()
        await ring.get_user()
        await ring.apply_stream(self.mode, interval=1.0)
        for message in encode_snapshot(ring):
            await self.broadcast(message)
        step = 0
        try:
            while True:
                step += 1
                _push_demo(firmware, step, self.mode)
                try:
                    while True:
                        message = queue.get_nowait()
                        if message:
                            await self.broadcast(message)
                except asyncio.QueueEmpty:
                    pass
                await asyncio.sleep(0.25)
        finally:
            self.ring = None
            self.firmware = None
            await ring.stop_realtime()
            await ring.disconnect()


def _profile_int(value, lo: int, hi: int, label: str) -> int:
    number = int(value)
    if number < lo or number > hi:
        raise ValueError(f"{label} ต้องอยู่ระหว่าง {lo}–{hi}")
    return number


def _i16(value: int) -> bytes:
    return int(value).to_bytes(2, "big", signed=True)


def _push_demo(firmware: SimulatedRing, step: int, mode: str) -> None:
    spec = resolve_mode(mode)
    if spec.hr in {"ble", "auto"}:
        bpm = 72 + int(8 * math.sin(step / 6))
        rr = (800 + int(20 * math.sin(step / 4)), 820 + int(18 * math.cos(step / 5)))
        firmware.push_heart_rate(bpm, rr)
    firmware.push_battery(max(20, 87 - step // 40))
    if spec.poll:
        steps = 1840 + step * 2
        distance = 12500 + step * 8
        calories = 37 + step // 3
        firmware.notify(
            UUID_FITNESS_RX,
            pack(
                CMD_GET_SPORT,
                steps.to_bytes(3, "big") + distance.to_bytes(3, "big") + calories.to_bytes(3, "big"),
            ),
        )
        if step % 4 == 0:
            firmware.notify(
                UUID_FITNESS_RX,
                pack(
                    CMD_GET_HEALTH,
                    bytes(
                        [
                            42 + int(2 * math.sin(step / 18)),
                            16 + int(2 * math.sin(step / 10)),
                            3,
                            4 + int(2 * math.sin(step / 12)),
                            80 + int(6 * math.cos(step / 14)),
                        ]
                    ),
                ),
            )
            body = 366 + int(4 * math.sin(step / 20))
            wrist = 312 + int(6 * math.sin(step / 16))
            ambient = 265 + int(8 * math.cos(step / 22))
            firmware.notify(
                UUID_FITNESS_RX,
                pack(
                    CMD_GET_TEMP,
                    ambient.to_bytes(2, "big") + wrist.to_bytes(2, "big") + body.to_bytes(2, "big"),
                ),
            )
            if spec.spo2:
                firmware.notify(UUID_FITNESS_RX, pack(CMD_SET_SPO2, bytes([1, 97 + (step // 20) % 3, 0, 0, 1])))
    if spec.raw:
        acc_x = 400 + int(180 * math.sin(step / 5))
        acc_y = 80 + int(90 * math.cos(step / 7))
        acc_z = 980 + int(40 * math.sin(step / 9))
        gyro_x = int(120 * math.sin(step / 4))
        gyro_y = int(90 * math.cos(step / 6))
        gyro_z = int(60 * math.sin(step / 8))
        ppg = 1180 + int(90 * math.sin(step / 2.2)) + int(40 * math.sin(step / 0.7))
        imu = _i16(acc_x) + _i16(acc_y) + _i16(acc_z) + _i16(gyro_x) + _i16(gyro_y) + _i16(gyro_z)
        payload = bytes([3]) + (step).to_bytes(4, "big") + bytes([12]) + imu + bytes([3, 1]) + ppg.to_bytes(3, "big")
        firmware.notify(UUID_FITNESS_RX, pack(RX_RAW_STREAM, payload))


hub = Hub()
app = FastAPI(title="Gadget Panda")


class NoCacheStatic(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        return response


app.mount("/static", NoCacheStatic(directory=STATIC), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(
        STATIC / "index.html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.websocket("/ws")
async def websocket_endpoint(socket: WebSocket) -> None:
    await socket.accept()
    hub.clients.add(socket)
    try:
        await hub.welcome(socket)
        while True:
            raw = await socket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if message.get("type") == "set_mode":
                await hub.set_mode(str(message.get("mode", "")))
            elif message.get("type") == "set_user":
                await hub.set_user(message)
    except WebSocketDisconnect:
        hub.clients.discard(socket)
    except Exception:
        hub.clients.discard(socket)


async def serve(
    host: str,
    port: int,
    address: str | None,
    timeout: float,
    demo: bool,
    mode: str = DEFAULT_MODE,
) -> None:
    from gadgetpanda.license import require as require_license

    require_license("ring.ui")
    import uvicorn

    hub.mode = resolve_mode(mode).id
    config = uvicorn.Config(app, host=host, port=port, log_level="warning", loop="asyncio")
    server = uvicorn.Server(config)
    worker = asyncio.create_task(hub.run_demo() if demo else hub.run_ring(address, timeout))
    try:
        await server.serve()
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
