"""Web remote UI for gadgetpanda.dog (FastAPI + WebSocket)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gadgetpanda.dog import Action, Dog, Move, OpcodeUnknown, UnsupportedCapability, by_id
from gadgetpanda.dog.protocol import PROGRAM_VERBS
from gadgetpanda.dog.testing import FakeDogBleClient, SimulatedDog

STATIC = Path(__file__).parent / "static"
log = logging.getLogger("gadgetpanda.dog.ui")


def _catalog(model: str = "x1") -> dict:
    profile = by_id(model)
    moves = [m.value for m in Move if profile.opcode_for(m)]
    actions = [a.value for a in Action if profile.opcode_for(a)]
    program = sorted(v.value for v in PROGRAM_VERBS)
    return {
        "type": "catalog",
        "model": profile.id,
        "display_name": profile.display_name,
        "moves": moves,
        "actions": actions,
        "program": program,
    }


class DogHub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.status = {"state": "idle", "name": "", "address": "", "model": "x1", "error": ""}
        self.dog: Dog | None = None
        self.firmware: SimulatedDog | None = None
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
        await socket.send_text(json.dumps(_catalog(self.status.get("model") or "x1"), ensure_ascii=False))

    async def _set_status(self, **fields: str) -> None:
        self.status.update(fields)
        await self.broadcast({"type": "status", **self.status})

    async def handle(self, message: dict) -> None:
        kind = message.get("type")
        try:
            if kind == "move":
                await self._move(str(message.get("name", "")))
            elif kind == "hold_start":
                await self._hold_start(str(message.get("name", "")))
            elif kind == "hold_stop":
                await self._hold_stop()
            elif kind == "action":
                await self._action(str(message.get("name", "")))
            elif kind == "program_run":
                verbs = message.get("verbs") or []
                if not isinstance(verbs, list):
                    raise ValueError("verbs must be a list")
                await self._program_run([str(v) for v in verbs])
            elif kind == "program_clear":
                await self._program_clear()
            elif kind == "raw":
                await self._raw(str(message.get("hex", "")))
            elif kind == "stop":
                await self._move("stop")
        except (OpcodeUnknown, UnsupportedCapability, ValueError, RuntimeError) as exc:
            await self.broadcast({"type": "error", "error": str(exc)})
        except Exception as exc:
            log.exception("dog ui command failed")
            await self.broadcast({"type": "error", "error": str(exc)})

    async def _require_dog(self) -> Dog:
        dog = self.dog
        if dog is None or not dog.connected:
            raise RuntimeError("ยังไม่ต่อสุนัข")
        return dog

    async def _move(self, name: str) -> None:
        dog = await self._require_dog()
        async with self._cmd_lock:
            await dog.move(name)
        await self.broadcast({"type": "tx", "kind": "move", "name": name})

    async def _hold_start(self, name: str) -> None:
        dog = await self._require_dog()
        async with self._cmd_lock:
            await dog.hold_move(name, seconds=None)
        await self.broadcast({"type": "tx", "kind": "hold_start", "name": name})

    async def _hold_stop(self) -> None:
        dog = await self._require_dog()
        async with self._cmd_lock:
            await dog.stop_hold()
            await dog.move(Move.STOP)
        await self.broadcast({"type": "tx", "kind": "hold_stop", "name": "stop"})

    async def _action(self, name: str) -> None:
        dog = await self._require_dog()
        async with self._cmd_lock:
            await dog.action(name)
        await self.broadcast({"type": "tx", "kind": "action", "name": name})

    async def _program_run(self, verbs: list[str]) -> None:
        dog = await self._require_dog()
        async with self._cmd_lock:
            await dog.run_program(verbs, step_delay=0.05)
        await self.broadcast({"type": "tx", "kind": "program_run", "verbs": verbs})

    async def _program_clear(self) -> None:
        dog = await self._require_dog()
        async with self._cmd_lock:
            await dog.enter_program_mode()
            await dog.program_clear()
            await dog.enter_remote_mode()
        await self.broadcast({"type": "tx", "kind": "program_clear"})

    async def _raw(self, hex_payload: str) -> None:
        dog = await self._require_dog()
        async with self._cmd_lock:
            await dog.raw_write(hex_payload)
        await self.broadcast({"type": "tx", "kind": "raw", "hex": hex_payload.replace(" ", "")})

    async def run_dog(
        self,
        address: str | None,
        timeout: float,
        *,
        demo: bool,
        model: str,
    ) -> None:
        while True:
            try:
                await self._set_status(state="connecting", error="", model=model)
                if demo:
                    firmware = SimulatedDog(name="X1-DEMO")
                    self.firmware = firmware
                    dog = Dog(firmware.advertised(), model=model, transport=FakeDogBleClient(firmware))
                    await dog.connect()
                else:
                    if address:
                        dog = Dog(address, model=model)
                    else:
                        dog = await Dog.find(timeout=timeout, model=model)
                    await dog.connect(timeout=timeout)
                self.dog = dog
                loop = asyncio.get_running_loop()

                def _on_rx(data: bytes) -> None:
                    payload = data.hex()
                    loop.call_soon_threadsafe(
                        lambda hex_payload=payload: asyncio.create_task(
                            self.broadcast({"type": "rx", "hex": hex_payload})
                        )
                    )

                def _on_disconnected(*_args) -> None:
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(
                            self._set_status(state="disconnected", error="ตัดการเชื่อมต่อ")
                        )
                    )

                dog.on("rx", _on_rx)
                dog.on("disconnected", _on_disconnected)
                await self._set_status(
                    state="connected",
                    name=dog.name or "",
                    address=dog.address,
                    model=dog.profile.id,
                    error="",
                )
                await self.broadcast(_catalog(dog.profile.id))
                while dog.connected:
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.exception("dog ui session ended")
                await self._set_status(state="error", error=str(exc))
                await asyncio.sleep(2.0)
            finally:
                dog = self.dog
                self.dog = None
                if dog is not None:
                    try:
                        await dog.disconnect()
                    except Exception:
                        pass


hub = DogHub()
app = FastAPI(title="Gadget Panda · Dog")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


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
            await hub.handle(message)
    except WebSocketDisconnect:
        hub.clients.discard(socket)
    except Exception:
        hub.clients.discard(socket)


async def serve(
    host: str,
    port: int,
    address: str | None,
    timeout: float,
    *,
    demo: bool = False,
    model: str = "x1",
) -> None:
    from gadgetpanda.license import require as require_license

    require_license("dog.ui")
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning", loop="asyncio")
    server = uvicorn.Server(config)
    runner = asyncio.create_task(hub.run_dog(address, timeout, demo=demo, model=model))
    try:
        await server.serve()
    finally:
        runner.cancel()
        try:
            await runner
        except asyncio.CancelledError:
            pass
