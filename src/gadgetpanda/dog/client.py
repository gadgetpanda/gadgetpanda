"""Async BLE host for multi-model fun dogs."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from gadgetpanda.dog.actions import ACTION_CAPABILITY, MOVE_CAPABILITY, Action, Move
from gadgetpanda.dog.capabilities import Capability, OpcodeUnknown, UnsupportedCapability
from gadgetpanda.dog.models import AdvertisedDog, DogProfile, EventBus, Handler
from gadgetpanda.dog.profiles import by_id, match_advertisement
from gadgetpanda.dog.protocol import (
    DEFAULT_NAME_FILTERS,
    HOLD_INTERVAL_S,
    PROGRAM_CLEAR,
    PROGRAM_ENTER,
    PROGRAM_EXIT_TO_REMOTE,
    PROGRAM_PLAY,
    PROGRAM_VERBS,
    codes_for,
    looks_like_dog,
    parse_hex_payload,
    program_frame,
)
from gadgetpanda.license import require as require_license

log = logging.getLogger("gadgetpanda.dog")


class Dog:
    """Async host for one fun-dog over GATT (FFE5 / FFE8 / FFE9)."""

    def __init__(
        self,
        device: BLEDevice | AdvertisedDog | str,
        name: str | None = None,
        *,
        model: str | DogProfile = "x1",
        transport: Any | None = None,
    ):
        if isinstance(device, AdvertisedDog):
            self.address = device.address
            self.name = device.display_name
            self.ble_name = device.name
        elif isinstance(device, str):
            self.address = device
            self.ble_name = name or device
            self.name = name or device
        else:
            self.address = device.address
            self.ble_name = device.name or name or device.address
            self.name = device.name or name or device.address

        self.profile = model if isinstance(model, DogProfile) else by_id(model)
        self.client: Any | None = None
        self._events = EventBus()
        self._lock = asyncio.Lock()
        self._transport = transport
        self.last_rx: bytes | None = None
        self.services: list[str] = []
        self._hold_task: asyncio.Task | None = None

    def on(self, event: str, handler: Handler) -> Dog:
        self._events.on(event, handler)
        return self

    @property
    def connected(self) -> bool:
        return bool(self.client and getattr(self.client, "is_connected", False))

    @property
    def capabilities(self):
        return self.profile.capabilities

    def supports(self, capability) -> bool:
        return self.profile.supports(capability)

    @classmethod
    async def scan(
        cls,
        timeout: float = 8.0,
        filters: tuple[str, ...] = DEFAULT_NAME_FILTERS,
        *,
        discover: Callable[..., Awaitable[list[AdvertisedDog]]] | None = None,
        loose: bool = False,
    ) -> list[AdvertisedDog]:
        """Scan for dog-like advertisements.

        When ``loose`` is True, return every BLE device (useful while learning names).
        """
        require_license("dog.scan")
        if discover is not None:
            found = await discover(timeout)
            if loose:
                return sorted(found, key=lambda item: item.rssi or -999, reverse=True)
            return sorted(
                [item for item in found if looks_like_dog(item.name, filters)],
                key=lambda item: item.rssi or -999,
                reverse=True,
            )

        found: dict[str, AdvertisedDog] = {}

        def _callback(device: BLEDevice, adv: AdvertisementData) -> None:
            name = adv.local_name or device.name
            if loose or looks_like_dog(name, filters):
                found[device.address] = AdvertisedDog(
                    name=name or "unknown",
                    address=device.address,
                    rssi=adv.rssi,
                )

        scanner = BleakScanner(detection_callback=_callback)
        await scanner.start()
        try:
            await asyncio.sleep(timeout)
        finally:
            await scanner.stop()
        return sorted(found.values(), key=lambda item: item.rssi or -999, reverse=True)

    @classmethod
    async def find(
        cls,
        timeout: float = 8.0,
        *,
        model: str = "x1",
        loose: bool = False,
        transport: Any | None = None,
    ) -> Dog:
        devices = await cls.scan(timeout=timeout, loose=loose)
        if not devices:
            raise RuntimeError("ไม่พบสุนัข — เปิด BLE และเปิดเครื่องให้ใกล้ ๆ")
        first = devices[0]
        profile = by_id(model) if model else match_advertisement(first.name)
        return cls(first, model=profile, transport=transport)

    async def connect(self, timeout: float = 20.0) -> None:
        require_license("dog.connect")
        if self._transport is not None:
            self.client = self._transport
            await self.client.connect()
        else:
            device = await self._resolve_device(timeout)
            if device is not None:
                if getattr(device, "name", None):
                    self.ble_name = device.name
                    self.name = device.name
            self.client = BleakClient(
                device or self.address,
                timeout=timeout,
                disconnected_callback=self._on_disconnected,
            )
            await self.client.connect()
        self._cache_services()
        await self._subscribe()
        self._events.emit("connected", self)

    async def _resolve_device(self, timeout: float):
        try:
            return await BleakScanner.find_device_by_address(self.address, timeout=min(12.0, timeout))
        except Exception:
            log.debug("resolve device failed", exc_info=True)
            return None

    def _on_disconnected(self, _client: BleakClient) -> None:
        self._events.emit("disconnected", self)

    def _cache_services(self) -> None:
        self.services = []
        client = self.client
        if client is None:
            return
        try:
            services = getattr(client, "services", None)
            if not services:
                return
            for svc in services:
                chars = []
                for ch in svc.characteristics:
                    props = ",".join(ch.properties)
                    chars.append(f"{ch.uuid}[{props}]")
                self.services.append(f"{svc.uuid}: " + "; ".join(chars))
        except Exception:
            log.debug("service cache failed", exc_info=True)

    async def disconnect(self) -> None:
        await self.stop_hold()
        client = self.client
        self.client = None
        if client is not None:
            try:
                if getattr(client, "is_connected", False):
                    await client.disconnect()
            except Exception:
                log.debug("disconnect ignored", exc_info=True)
        self._events.emit("disconnected", self)

    async def __aenter__(self) -> Dog:
        await self.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.disconnect()

    async def _subscribe(self) -> None:
        assert self.client is not None
        uuid = self.profile.uuids.notify

        def _on_notify(_char: BleakGATTCharacteristic, data: bytearray) -> None:
            payload = bytes(data)
            self.last_rx = payload
            self._events.emit("rx", payload)

        try:
            await self.client.start_notify(uuid, _on_notify)
        except Exception as exc:
            log.warning("notify subscribe failed on %s: %s", uuid, exc)
            self._events.emit("error", exc)

    async def raw_write(self, data: bytes | str, *, response: bool | None = None) -> None:
        """Write raw bytes (or hex string) to the model's write characteristic."""
        require_license("dog.raw")
        await self._gatt_write(data, response=response)

    async def _gatt_write(self, data: bytes | str, *, response: bool | None = None) -> None:
        if isinstance(data, str):
            data = parse_hex_payload(data)
        if not data:
            raise ValueError("empty payload")
        client = self.client
        if client is None or not getattr(client, "is_connected", False):
            raise RuntimeError("dog is not connected")
        async with self._lock:
            if response is None:
                try:
                    await client.write_gatt_char(self.profile.uuids.write, data, response=False)
                except Exception:
                    await client.write_gatt_char(self.profile.uuids.write, data, response=True)
            else:
                await client.write_gatt_char(self.profile.uuids.write, data, response=response)
        self._events.emit("tx", data)

    async def action(self, verb: Action | str) -> None:
        require_license("dog.action")
        key = str(verb.value if isinstance(verb, Action) else verb).strip().lower()
        try:
            action = verb if isinstance(verb, Action) else Action(key)
        except ValueError:
            # Convenience: allow move names through action() for CLI mistakes.
            try:
                await self.move(key)
                return
            except ValueError as exc:
                raise ValueError(f"{key!r} is not a valid Action or Move") from exc
        await self._send_verb(action, ACTION_CAPABILITY[action])

    async def move(self, verb: Move | str) -> None:
        require_license("dog.move")
        move = verb if isinstance(verb, Move) else Move(str(verb).strip().lower())
        if move is Move.STOP:
            await self.stop_hold()
        await self._send_verb(move, MOVE_CAPABILITY[move])

    async def _send_verb(self, verb: Action | Move, capability) -> None:
        if not self.profile.supports(capability):
            raise UnsupportedCapability(self.profile.id, capability)
        payload = self.profile.opcode_for(verb)
        if payload is None:
            raise OpcodeUnknown(self.profile.id, verb.value if hasattr(verb, "value") else str(verb))
        await self._gatt_write(payload)

    def _resolve_verb(self, verb: Action | Move | str) -> Action | Move:
        if isinstance(verb, (Action, Move)):
            return verb
        key = str(verb).strip().lower()
        try:
            return Action(key)
        except ValueError:
            return Move(key)

    async def hold_move(
        self,
        verb: Move | str,
        *,
        seconds: float | None = None,
        interval: float = HOLD_INTERVAL_S,
    ) -> None:
        """Repeat a direction frame like the remote 50 ms hold timer.

        If ``seconds`` is None, keep sending until ``stop_hold()`` / ``move stop``.
        """
        require_license("dog.move")
        move = verb if isinstance(verb, Move) else Move(str(verb).strip().lower())
        if move is Move.STOP:
            await self.stop_hold()
            await self.move(Move.STOP)
            return
        payload = self.profile.opcode_for(move)
        if payload is None:
            raise OpcodeUnknown(self.profile.id, move.value)
        if not self.profile.supports(MOVE_CAPABILITY[move]):
            raise UnsupportedCapability(self.profile.id, MOVE_CAPABILITY[move])

        await self.stop_hold()

        async def _loop() -> None:
            deadline = None if seconds is None else asyncio.get_running_loop().time() + seconds
            try:
                while True:
                    await self._gatt_write(payload)
                    if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                        break
                    await asyncio.sleep(interval)
            except asyncio.CancelledError:
                raise
            finally:
                if seconds is not None:
                    try:
                        await self.move(Move.STOP)
                    except Exception:
                        log.debug("hold stop ignored", exc_info=True)

        self._hold_task = asyncio.create_task(_loop(), name="dog-hold-move")
        if seconds is not None:
            await self._hold_task
            self._hold_task = None

    async def stop_hold(self) -> None:
        task = self._hold_task
        self._hold_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def enter_program_mode(self) -> None:
        self._require_program()
        await self._gatt_write(PROGRAM_ENTER)

    async def enter_remote_mode(self) -> None:
        self._require_program()
        await self._gatt_write(PROGRAM_EXIT_TO_REMOTE)

    async def program_clear(self) -> None:
        self._require_program()
        await self._gatt_write(PROGRAM_CLEAR)

    async def program_play(self) -> None:
        self._require_program()
        await self._gatt_write(PROGRAM_PLAY)

    async def program_add(self, verb: Action | Move | str) -> None:
        """Enqueue one step in program mode (``0xB2`` + same op/action as remote)."""
        self._require_program()
        resolved = self._resolve_verb(verb)
        if resolved not in PROGRAM_VERBS:
            raise OpcodeUnknown(self.profile.id, getattr(resolved, "value", str(resolved)))
        op, act = codes_for(resolved)
        await self._gatt_write(program_frame(op, act))

    async def run_program(
        self,
        verbs: list[Action | Move | str],
        *,
        clear: bool = True,
        enter: bool = True,
        play: bool = True,
        exit_to_remote: bool = False,
        step_delay: float = 0.05,
    ) -> None:
        """Upload a sequence then play it (program-mode flow)."""
        self._require_program()
        if enter:
            await self.enter_program_mode()
            await asyncio.sleep(step_delay)
        if clear:
            await self.program_clear()
            await asyncio.sleep(step_delay)
        for verb in verbs:
            await self.program_add(verb)
            await asyncio.sleep(step_delay)
        if play:
            await self.program_play()
        if exit_to_remote:
            await asyncio.sleep(step_delay)
            await self.enter_remote_mode()

    def _require_program(self) -> None:
        require_license("dog.program")
        if not self.profile.supports(Capability.PROGRAM_SEQUENCE):
            raise UnsupportedCapability(self.profile.id, Capability.PROGRAM_SEQUENCE)
