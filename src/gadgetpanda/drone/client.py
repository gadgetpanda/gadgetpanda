"""Async Wi‑Fi host for V66 / FLOW-UFO style mini drones."""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

from gadgetpanda.drone.actions import Command, Stick
from gadgetpanda.drone.capabilities import Capability, UnsupportedCapability
from gadgetpanda.drone.models import AdvertisedDrone, DroneProfile, EventBus, Handler
from gadgetpanda.drone.profiles import by_id
from gadgetpanda.drone.protocol import (
    CENTER,
    HEARTBEAT,
    HEARTBEAT_INTERVAL_S,
    SEND_INTERVAL_S,
    STOP_CONTROL,
    StickState,
    build_stick_frame,
    clamp_axis,
    parse_hex_payload,
)
from gadgetpanda.license import require as require_license

log = logging.getLogger("gadgetpanda.drone")


async def tcp_probe(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except Exception:
        return False
    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass
    return True


async def icmp_ping(host: str, timeout: float = 1.0) -> bool:
    """Best-effort ICMP via system ping (no root socket required)."""
    import subprocess

    def _ping() -> bool:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(max(1, int(timeout * 1000))), host],
            capture_output=True,
            timeout=timeout + 1.0,
            check=False,
        )
        return result.returncode == 0

    try:
        return await asyncio.to_thread(_ping)
    except Exception:
        return False


async def host_reachable(host: str, timeout: float = 1.5) -> tuple[bool, str]:
    """Confirm the craft gateway is actually there (UDP send-only is a false friend).

    Require TCP to the RTSP/camera port (or alt :5000). ICMP alone is rejected —
    home LAN can route ``192.168.1.1`` and pass ping while UDP stick TX fails with
    Errno 49 / no coordinated flight / no camera.
    """
    if await tcp_probe(host, 7070, timeout=timeout):
        return True, "tcp:7070"
    if await tcp_probe(host, 5000, timeout=timeout):
        return True, "tcp:5000"
    return False, "no tcp:7070/5000 — join FLOW-UFO / craft Wi‑Fi first"


class _UdpTransport:
    def __init__(self) -> None:
        self.host = ""
        self.port = 0
        self.is_connected = False
        self._sock: socket.socket | None = None

    async def connect(self, host: str, port: int, timeout: float = 2.0) -> None:
        ok, how = await host_reachable(host, timeout=timeout)
        if not ok:
            raise ConnectionError(
                f"โดรนไม่ตอบที่ {host} ({how}) — join Wi‑Fi hotspot ของโดรนก่อน "
                f"(เช่น FLOW-UFO-…) แล้วลองใหม่"
            )
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        self._sock = sock
        self.host = host
        self.port = port
        await asyncio.wait_for(self.send(HEARTBEAT), timeout=timeout)
        self.is_connected = True
        log.info("udp up %s:%s via %s", host, port, how)

    async def disconnect(self) -> None:
        self.is_connected = False
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    async def send(self, data: bytes) -> None:
        if self._sock is None:
            raise RuntimeError("UDP socket not open")
        loop = asyncio.get_running_loop()
        await loop.sock_sendto(self._sock, data, (self.host, self.port))


class Drone:
    """Async host for one Wi‑Fi mini drone (UDP stick loop)."""

    def __init__(
        self,
        host: str | AdvertisedDrone | None = None,
        *,
        model: str | DroneProfile = "flow",
        port: int | None = None,
        transport: Any | None = None,
        demo: bool = False,
    ):
        self.profile = model if isinstance(model, DroneProfile) else by_id(model)
        if isinstance(host, AdvertisedDrone):
            self.host = host.host
            self.port = host.udp_port
        else:
            self.host = host or self.profile.endpoints.host
            self.port = port or self.profile.endpoints.udp_port

        self.name = self.profile.display_name
        self.address = f"{self.host}:{self.port}"
        self._events = EventBus()
        self._transport = transport
        self._demo = demo
        self._lock = asyncio.Lock()
        self._tick_task: asyncio.Task | None = None
        self._pulse_task: asyncio.Task | None = None
        self._connected = False
        self.last_tx: bytes | None = None
        self.state = StickState()
        self._armed = False

    def on(self, event: str, handler: Handler) -> Drone:
        self._events.on(event, handler)
        return self

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def capabilities(self):
        return self.profile.capabilities

    def supports(self, capability: Capability) -> bool:
        return self.profile.supports(capability)

    def _require(self, capability: Capability) -> None:
        if not self.supports(capability):
            raise UnsupportedCapability(f"{self.profile.id} lacks {capability.value}")

    @classmethod
    async def probe(
        cls,
        host: str | None = None,
        port: int | None = None,
        *,
        model: str = "flow",
        timeout: float = 1.5,
    ) -> AdvertisedDrone:
        profile = by_id(model)
        target_host = host or profile.endpoints.host
        target_port = port or profile.endpoints.udp_port
        ok, how = await host_reachable(target_host, timeout=timeout)
        return AdvertisedDrone(
            host=target_host,
            udp_port=target_port,
            reachable=ok,
            note=how if ok else f"down ({how})",
        )

    @classmethod
    async def scan(
        cls,
        timeout: float = 1.5,
        *,
        model: str = "flow",
        hosts: tuple[str, ...] | None = None,
    ) -> list[AdvertisedDrone]:
        """Probe common AP gateway IPs (drone is usually 192.168.1.1 after join)."""
        require_license("drone.scan")
        profile = by_id(model)
        candidates = hosts or (
            profile.endpoints.host,
            "192.168.0.1",
            "192.168.4.1",
        )
        found: list[AdvertisedDrone] = []
        for host in candidates:
            item = await cls.probe(host, profile.endpoints.udp_port, model=model, timeout=timeout)
            found.append(item)
        return found

    async def connect(self, timeout: float = 3.0) -> None:
        require_license("drone.connect")
        if self._connected:
            return
        if self._demo:
            from gadgetpanda.drone.testing import FakeDroneTransport

            self._transport = FakeDroneTransport()
        elif self._transport is None:
            self._transport = _UdpTransport()
        await self._transport.connect(self.host, self.port, timeout=timeout)
        self._connected = True
        self._armed = True
        self.state = StickState(fixed_height=bool(self.profile.default_fixed_height))
        self._tick_task = asyncio.create_task(self._tick_loop(), name="drone-tick")
        if self.supports(Capability.HEARTBEAT):
            self._pulse_task = asyncio.create_task(self._heartbeat_loop(), name="drone-hb")
        self._events.emit("connected", self)
        log.info(
            "drone connected %s model=%s frame=%s fixed_height=%s",
            self.address,
            self.profile.id,
            self.profile.frame_variant,
            self.state.fixed_height,
        )

    async def disconnect(self) -> None:
        self._armed = False
        await self.hover()
        await self._cancel_tasks()
        if self._connected and self.supports(Capability.STICK):
            try:
                await self._udp_write(STOP_CONTROL)
            except Exception:
                pass
        if self._transport is not None:
            await self._transport.disconnect()
        was = self._connected
        self._connected = False
        if was:
            self._events.emit("disconnected", self)

    async def __aenter__(self) -> Drone:
        await self.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.disconnect()

    async def _cancel_tasks(self) -> None:
        for task in (self._tick_task, self._pulse_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._tick_task = None
        self._pulse_task = None

    async def _tick_loop(self) -> None:
        failures = 0
        try:
            while self._connected and self._armed:
                try:
                    await self._send_stick()
                    failures = 0
                except OSError as exc:
                    failures += 1
                    self._events.emit("error", exc)
                    if failures == 1 or failures % 40 == 0:
                        log.warning(
                            "drone stick TX failed (%s) — ตรวจว่า Mac อยู่บน Wi‑Fi โดรน (FLOW-UFO) "
                            "และ rtsp://%s:7070 เปิดได้",
                            exc,
                            self.host,
                        )
                    await asyncio.sleep(min(1.0, SEND_INTERVAL_S * failures))
                    continue
                await asyncio.sleep(SEND_INTERVAL_S)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._events.emit("error", exc)
            log.exception("drone tick failed")

    async def _heartbeat_loop(self) -> None:
        try:
            while self._connected:
                try:
                    await self._udp_write(HEARTBEAT)
                except OSError as exc:
                    log.debug("drone heartbeat TX failed: %s", exc)
                await asyncio.sleep(HEARTBEAT_INTERVAL_S)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._events.emit("error", exc)

    async def _send_stick(self) -> None:
        frame = build_stick_frame(self.state, variant=self.profile.frame_variant, udp_wrap=True)
        await self._udp_write(frame)

    async def raw_write(self, data: bytes | str) -> None:
        require_license("drone.raw")
        await self._udp_write(data)

    async def _udp_write(self, data: bytes | str) -> None:
        payload = parse_hex_payload(data) if isinstance(data, str) else data
        if not self._connected or self._transport is None:
            raise RuntimeError("drone not connected")
        async with self._lock:
            await self._transport.send(payload)
            self.last_tx = payload
        self._events.emit("tx", payload)

    def set_axes(
        self,
        *,
        roll: int | None = None,
        pitch: int | None = None,
        throttle: int | None = None,
        yaw: int | None = None,
    ) -> None:
        require_license("drone.stick")
        self._require(Capability.STICK)
        self.state = StickState(
            roll=clamp_axis(roll) if roll is not None else self.state.roll,
            pitch=clamp_axis(pitch) if pitch is not None else self.state.pitch,
            throttle=clamp_axis(throttle) if throttle is not None else self.state.throttle,
            yaw=clamp_axis(yaw) if yaw is not None else self.state.yaw,
            takeoff=self.state.takeoff,
            land=self.state.land,
            emergency=self.state.emergency,
            circle=self.state.circle,
            headless=self.state.headless,
            unlock_or_return=self.state.unlock_or_return,
            light=self.state.light,
            calibrate=self.state.calibrate,
            gesture=self.state.gesture,
            fixed_height=self.state.fixed_height,
        )

    async def hover(self) -> None:
        self._require(Capability.STICK)
        self.state = StickState(
            roll=CENTER,
            pitch=CENTER,
            throttle=CENTER,
            yaw=CENTER,
            headless=self.state.headless,
            light=self.state.light,
            fixed_height=self.state.fixed_height,
        )

    async def stick(self, verb: Stick | str) -> None:
        require_license("drone.stick")
        self._require(Capability.STICK)
        name = verb.value if isinstance(verb, Stick) else str(verb).strip().lower()
        try:
            preset = Stick(name)
        except ValueError as exc:
            raise ValueError(f"unknown stick {name!r}") from exc
        delta = self.profile.stick_deflection
        axes = {
            Stick.HOVER: (CENTER, CENTER, CENTER, CENTER),
            Stick.FORWARD: (CENTER, CENTER + delta, CENTER, CENTER),
            Stick.BACKWARD: (CENTER, CENTER - delta, CENTER, CENTER),
            Stick.LEFT: (CENTER - delta, CENTER, CENTER, CENTER),
            Stick.RIGHT: (CENTER + delta, CENTER, CENTER, CENTER),
            Stick.UP: (CENTER, CENTER, CENTER + delta, CENTER),
            Stick.DOWN: (CENTER, CENTER, CENTER - delta, CENTER),
            Stick.YAW_LEFT: (CENTER, CENTER, CENTER, CENTER - delta),
            Stick.YAW_RIGHT: (CENTER, CENTER, CENTER, CENTER + delta),
        }[preset]
        self.set_axes(roll=axes[0], pitch=axes[1], throttle=axes[2], yaw=axes[3])

    async def hold_stick(self, verb: Stick | str, *, seconds: float | None = None) -> None:
        await self.stick(verb)
        if seconds is None:
            return
        await asyncio.sleep(seconds)
        await self.hover()

    async def _pulse_flag(self, **flags: bool) -> None:
        base = self.state
        self.state = StickState(
            roll=base.roll,
            pitch=base.pitch,
            throttle=base.throttle,
            yaw=base.yaw,
            takeoff=flags.get("takeoff", base.takeoff),
            land=flags.get("land", base.land),
            emergency=flags.get("emergency", base.emergency),
            circle=flags.get("circle", base.circle),
            headless=flags.get("headless", base.headless),
            unlock_or_return=flags.get("unlock_or_return", base.unlock_or_return),
            light=flags.get("light", base.light),
            calibrate=flags.get("calibrate", base.calibrate),
            gesture=flags.get("gesture", base.gesture),
            fixed_height=flags.get("fixed_height", base.fixed_height),
        )

    async def command(self, verb: Command | str) -> None:
        require_license("drone.cmd")
        name = verb.value if isinstance(verb, Command) else str(verb).strip().lower()
        try:
            cmd = Command(name)
        except ValueError as exc:
            raise ValueError(f"unknown command {name!r}") from exc

        if cmd == Command.TAKEOFF:
            self._require(Capability.TAKEOFF)
            await self._pulse_flag(takeoff=True, land=False, emergency=False)
            await asyncio.sleep(1.0)
            await self._pulse_flag(takeoff=False)
            return
        if cmd == Command.LAND:
            self._require(Capability.LAND)
            await self._pulse_flag(land=True, takeoff=False)
            await asyncio.sleep(1.0)
            await self._pulse_flag(land=False)
            await self.hover()
            return
        if cmd == Command.STOP:
            await self.hover()
            return
        if cmd == Command.EMERGENCY:
            self._require(Capability.EMERGENCY)
            await self._pulse_flag(emergency=True, takeoff=False, land=False)
            await asyncio.sleep(0.8)
            await self._pulse_flag(emergency=False)
            await self.hover()
            return
        if cmd == Command.HEADLESS_ON:
            self._require(Capability.HEADLESS)
            await self._pulse_flag(headless=True)
            return
        if cmd == Command.HEADLESS_OFF:
            self._require(Capability.HEADLESS)
            await self._pulse_flag(headless=False)
            return
        if cmd == Command.CALIBRATE:
            self._require(Capability.CALIBRATE)
            await self._pulse_flag(calibrate=True)
            await asyncio.sleep(1.0)
            await self._pulse_flag(calibrate=False)
            return
        if cmd == Command.LIGHT_ON:
            self._require(Capability.LIGHT)
            await self._pulse_flag(light=True)
            return
        if cmd == Command.LIGHT_OFF:
            self._require(Capability.LIGHT)
            await self._pulse_flag(light=False)
            return
        raise ValueError(f"unhandled command {cmd}")
