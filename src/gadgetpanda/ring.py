from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from gadgetpanda.models import (
    AdvertisedRing,
    BloodOxygen,
    EventBus,
    Handler,
    HeartRate,
    HrvTracker,
    PpgHrTracker,
    brand_display,
    panda_display_name,
)
from gadgetpanda.license import require as require_license
from gadgetpanda.stream import DEFAULT_MODE, resolve_mode
from gadgetpanda.protocol import (
    CMD_GET_BIRTHDAY,
    CMD_GET_HEALTH,
    CMD_GET_HEALTH_HISTORY,
    CMD_GET_HR_HISTORY,
    CMD_GET_PPG_HISTORY,
    CMD_GET_SLEEP,
    CMD_GET_SPORT,
    CMD_GET_SPORT_HISTORY,
    CMD_GET_TEMP,
    CMD_GET_USER,
    CMD_RAW,
    CMD_RESTORE,
    CMD_SET_BIRTHDAY,
    CMD_SET_SPO2,
    CMD_SET_UTC,
    CMD_SET_USER,
    CMD_SPORT_OFF,
    CMD_SPORT_ON,
    NAME_FILTERS,
    UUID_BATTERY_LEVEL,
    UUID_DIS_FIRMWARE,
    UUID_DIS_HARDWARE,
    UUID_DIS_MODEL,
    UUID_DIS_SERIAL,
    UUID_DIS_SOFTWARE,
    UUID_DIS_SYSTEM,
    UUID_DIS_VENDOR,
    UUID_FITNESS_RX,
    UUID_FITNESS_TX,
    UUID_HR_CONTROL,
    UUID_HR_MEASUREMENT,
    begin_utc_bytes,
    increment_mac,
    looks_like_ring,
    pack,
    pack_dfu,
    parse_ascii,
    parse_heart_rate,
    parse_rx,
    parse_system_id,
    take_frames,
    utc_bytes,
)

log = logging.getLogger("gadgetpanda")
_SOFT_ADT_ONWRIST = re.compile(r"SoftAdtGreen_onwrist\s*=\s*(\d+)", re.I)


class Ring:
    """Async host for one RING503PANDA / Gadget Panda ring."""

    def __init__(
        self,
        device: BLEDevice | AdvertisedRing | str,
        name: str | None = None,
        *,
        transport: Any | None = None,
    ):
        if isinstance(device, AdvertisedRing):
            self.address = device.address
            self.name = device.display_name
            self.ble_name = device.name
        elif isinstance(device, str):
            self.address = device
            self.ble_name = name or device
            self.name = panda_display_name(name, device)
        else:
            self.address = device.address
            self.ble_name = device.name or name or device.address
            self.name = panda_display_name(device.name or name, device.address)
        self.client: Any | None = None
        self.info: dict[str, str] = {}
        self.battery: int | None = None
        self.heart_rate = None
        self.hrv = None
        self.sport = None
        self.health = None
        self.temperature = None
        self.spo2 = None
        self.user = None
        self.raw = None
        self.imu = None
        self.ppg = None
        self._events = EventBus()
        self._lock = asyncio.Lock()
        self._transport = transport
        self._rx_buf = bytearray()
        self._realtime_on = False
        self._realtime_task: asyncio.Task | None = None
        self._hr_history_tried = False
        self._realtime_started = 0.0
        self._hrv = HrvTracker()
        self._ppg_hr = PpgHrTracker()
        self._ble_hr_at = 0.0
        self._hr_enable_at = 0.0
        self._last_raw_at = 0.0
        self._last_spo2_at = 0.0
        self._spo2_kick_at = 0.0
        self._spo2_holding = False
        self._spo2_hr_released = False
        self._optical_on_wrist = None
        self.stream_mode = DEFAULT_MODE
        self.hr_source = resolve_mode(DEFAULT_MODE).hr

    def on(self, event: str, handler: Handler) -> "Ring":
        self._events.on(event, handler)
        return self

    @classmethod
    async def scan(
        cls,
        timeout: float = 8.0,
        filters: tuple[str, ...] = NAME_FILTERS,
        *,
        discover: Callable[..., Awaitable[list[AdvertisedRing]]] | None = None,
    ) -> list[AdvertisedRing]:
        require_license("ring.scan")
        if discover is not None:
            found = await discover(timeout)
            return sorted(
                [item for item in found if looks_like_ring(item.name, filters)],
                key=lambda item: item.rssi or -999,
                reverse=True,
            )

        found: dict[str, AdvertisedRing] = {}

        def _callback(device: BLEDevice, adv: AdvertisementData) -> None:
            name = adv.local_name or device.name
            if looks_like_ring(name, filters):
                found[device.address] = AdvertisedRing(
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
        discover: Callable[..., Awaitable[list[AdvertisedRing]]] | None = None,
        transport: Any | None = None,
    ) -> "Ring":
        devices = await cls.scan(timeout=timeout, discover=discover)
        if not devices:
            raise TimeoutError("ไม่พบแหวน RING503PANDA / RING503nPANDA — เปิดแหวนแล้วสแกนใหม่")
        return cls(devices[0], transport=transport)

    async def __aenter__(self) -> "Ring":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.disconnect()

    async def connect(self, timeout: float = 20.0) -> None:
        require_license("ring.connect")
        if self._transport is not None:
            self.client = self._transport
        else:
            device = await self._resolve_device(timeout)
            self.client = BleakClient(
                device or self.address,
                timeout=timeout,
                disconnected_callback=self._on_disconnected,
            )
        await self.client.connect()
        await self._read_profile()
        request_mtu = getattr(self.client, "request_mtu", None)
        if callable(request_mtu):
            try:
                await request_mtu(517)
            except Exception:
                log.debug("mtu 517 not available")
        await self._subscribe()
        await self.set_utc()
        self._events.emit("connected", self)

    async def _resolve_device(self, timeout: float):
        try:
            return await BleakScanner.find_device_by_address(self.address, timeout=min(8.0, timeout))
        except Exception:
            return None

    async def disconnect(self) -> None:
        await self._cancel_realtime()
        self._hrv.reset()
        self._ppg_hr.reset()
        self._ble_hr_at = 0.0
        client = self.client
        self.client = None
        self._rx_buf.clear()
        if client is not None:
            try:
                if getattr(client, "is_connected", False):
                    await client.disconnect()
            except Exception:
                log.debug("disconnect ignored", exc_info=True)
        self._events.emit("disconnected", self)

    @property
    def connected(self) -> bool:
        return bool(self.client and self.client.is_connected)

    async def set_utc(self, when: datetime | None = None) -> None:
        await self._write(pack(CMD_SET_UTC, utc_bytes(when)))

    async def get_sport(self) -> None:
        await self._write(pack(CMD_GET_SPORT))

    async def get_health(self) -> None:
        await self._write(pack(CMD_GET_HEALTH))

    async def get_temperature(self) -> None:
        await self._write(pack(CMD_GET_TEMP))

    async def set_spo2(self, enabled: bool) -> None:
        await self._write(pack(CMD_SET_SPO2, bytes([1 if enabled else 0, 0])))

    async def set_sport_mode(self, enabled: bool) -> None:
        if enabled:
            await self._write(pack(CMD_SPORT_ON, bytes([4])))
        else:
            await self._write(pack(CMD_SPORT_OFF, bytes([0, 12])))

    async def get_user(self) -> None:
        require_license("ring.user")
        await self._write(pack(CMD_GET_USER, bytes([0])))

    async def set_user(
        self,
        age: int,
        sex: int | None = None,
        weight_kg: int | None = None,
        height_cm: int | None = None,
        user_id: int | None = None,
    ) -> None:
        require_license("ring.user")
        current = self.user
        resolved_sex = 1 if sex is None else sex
        resolved_weight = 70 if weight_kg is None else weight_kg
        resolved_height = 170 if height_cm is None else height_cm
        resolved_id = 1 if user_id is None else user_id
        if current is not None:
            if sex is None:
                resolved_sex = current.sex
            if weight_kg is None:
                resolved_weight = current.weight_kg
            if height_cm is None:
                resolved_height = current.height_cm
            if user_id is None:
                resolved_id = current.user_id
        payload = bytes(
            [int(age) & 0xFF, int(resolved_sex) & 0xFF, int(resolved_weight) & 0xFF, int(resolved_height) & 0xFF]
        ) + (int(resolved_id) & 0xFFFFFFFFFF).to_bytes(5, "big")
        await self._write(pack(CMD_SET_USER, payload))

    async def get_birthday(self) -> None:
        await self._write(pack(CMD_GET_BIRTHDAY, bytes([0])))

    async def set_birthday(self, year: int, month: int, day: int) -> None:
        await self._write(pack(CMD_SET_BIRTHDAY, year.to_bytes(2, "big") + bytes([month, day])))

    async def set_raw_enabled(self, enabled: bool) -> None:
        await self._write(pack(CMD_RAW, bytes([1, 1 if enabled else 0])))

    async def start_ppg(self) -> None:
        """Enable the optical front-end and 0x99 realtime PPG/IMU stream."""
        require_license("ring.ppg")
        await self.apply_stream("ppg")

    async def start_realtime(self, interval: float = 2.0) -> None:
        """Enable every live sensor and keep polling values that do not notify."""
        require_license("ring.stream")
        if self._realtime_on and self.stream_mode == "all":
            return
        await self.apply_stream("all", interval)

    async def apply_stream(self, mode: str = DEFAULT_MODE, interval: float = 1.5) -> None:
        """Switch the live sensors the ring is asked to send."""
        spec = resolve_mode(mode)
        await self._cancel_realtime()
        self.stream_mode = spec.id
        self.hr_source = spec.hr
        self._hr_history_tried = False
        self._realtime_started = time.monotonic()
        self._ppg_hr.reset()
        if spec.hr != "ble":
            self._ble_hr_at = 0.0
        if spec.sport_mode:
            try:
                await self.set_sport_mode(True)
            except Exception:
                log.debug("sport mode not available")
        else:
            try:
                await self.set_sport_mode(False)
            except Exception:
                log.debug("sport mode off ignored")
        if spec.hr_enable:
            await self._enable_heart_rate()
        await self._configure_optical(raw=spec.raw, spo2=spec.spo2)
        self._realtime_on = True
        if spec.poll or spec.hr_enable or spec.raw:
            if spec.poll:
                await self._poll_vitals()
            self._realtime_task = asyncio.create_task(self._realtime_loop(interval), name="panda-realtime")

    async def _configure_optical(self, *, raw: bool, spo2: bool) -> None:
        """PPG/IMU raw and SpO₂ share the optical front-end — never enable both."""
        if raw and spo2:
            spo2 = False
        try:
            if raw:
                await self.set_spo2(False)
                self._spo2_holding = False
                self.spo2 = None
                # SoftAdtGreen needs a beat to release the LED before 0x99 starts.
                await asyncio.sleep(0.8)
                await self.set_raw_enabled(True)
                await asyncio.sleep(0.4)
                await self.set_raw_enabled(True)
                self._last_raw_at = time.monotonic()
            elif spo2:
                await self.set_raw_enabled(False)
                await asyncio.sleep(0.35)
                await self.set_spo2(True)
                await asyncio.sleep(0.35)
                await self.set_spo2(True)  # sample apps often need a second enable
                self._spo2_kick_at = time.monotonic()
                self._last_spo2_at = 0.0
                self._spo2_holding = True
                self._spo2_hr_released = False
                self._optical_on_wrist = None
            else:
                await self.set_raw_enabled(False)
                await self.set_spo2(False)
                self._spo2_holding = False
        except Exception:
            log.debug("optical configure failed", exc_info=True)

    async def stop_realtime(self) -> None:
        await self._cancel_realtime()
        if not self.connected:
            return
        for action in (
            lambda: self.set_raw_enabled(False),
            lambda: self.set_spo2(False),
            lambda: self.set_sport_mode(False),
        ):
            try:
                await action()
            except Exception:
                log.debug("stop realtime ignored", exc_info=True)

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "address": self.address,
            "battery": self.battery,
            "heart_rate": self.heart_rate,
            "hrv": self.hrv,
            "sport": self.sport,
            "health": self.health,
            "temperature": self.temperature,
            "spo2": self.spo2,
            "user": self.user,
            "imu": self.imu,
            "ppg": self.ppg,
            "info": dict(self.info),
        }

    async def _enable_heart_rate(self) -> None:
        if not self.client:
            return
        self._hr_enable_at = time.monotonic()
        try:
            await self.client.write_gatt_char(UUID_HR_CONTROL, bytes([0x01]), response=True)
        except Exception:
            try:
                await self.client.write_gatt_char(UUID_HR_CONTROL, bytes([0x01]), response=False)
            except Exception:
                log.debug("heart rate control point not available")
        try:
            value = await self.client.read_gatt_char(UUID_HR_MEASUREMENT)
            if value:
                self._on_heart_rate(None, bytearray(value))
        except Exception:
            log.debug("heart rate read not available")

    async def _poll_vitals(self) -> None:
        spec = resolve_mode(self.stream_mode)
        if spec.poll:
            # While SpO₂ runs, avoid sport polls — they contend on the optical path.
            actions = (self.get_health, self.get_temperature) if spec.spo2 else (self.get_sport, self.get_health, self.get_temperature)
            for action in actions:
                if not self.connected:
                    return
                try:
                    await action()
                except Exception:
                    log.debug("vital poll failed", exc_info=True)
        quiet = time.monotonic() - self._ble_hr_at
        if spec.hr_enable and self.connected and quiet > 8.0 and time.monotonic() - self._hr_enable_at > 8.0:
            await self._enable_heart_rate()

    async def _realtime_loop(self, interval: float) -> None:
        try:
            while self.connected and self._realtime_on:
                await asyncio.sleep(interval)
                if not (self.connected and self._realtime_on):
                    return
                await self._poll_vitals()
                spec = resolve_mode(self.stream_mode)
                # Raw PPG/IMU can stall after SpO₂ / link noise — re-assert enable.
                if spec.raw and time.monotonic() - self._last_raw_at > 6.0:
                    try:
                        await self.set_spo2(False)
                        await self.set_raw_enabled(True)
                        self._last_raw_at = time.monotonic()
                    except Exception:
                        log.debug("raw keepalive failed", exc_info=True)
                # SpO₂ LED blocks BLE HR on this firmware. Duty-cycle:
                # measure until we have a %, pause SpO₂ so HR can stream, refresh SpO₂ later.
                if spec.spo2:
                    has_spo2 = bool(self.spo2 and self.spo2.spo2 > 0)
                    now = time.monotonic()
                    if not has_spo2 and now - self._spo2_kick_at > 10.0:
                        try:
                            await self.set_raw_enabled(False)
                            await self.set_spo2(True)
                            self._spo2_kick_at = now
                            self._spo2_holding = True
                        except Exception:
                            log.debug("spo2 keepalive failed", exc_info=True)
                    elif has_spo2 and self._spo2_holding and not self._spo2_hr_released:
                        await self._release_spo2_for_hr()
                    elif has_spo2 and not self._spo2_holding and now - self._last_spo2_at > 90.0:
                        try:
                            await self.set_spo2(True)
                            self._spo2_kick_at = now
                            self._spo2_holding = True
                            self._spo2_hr_released = False
                        except Exception:
                            log.debug("spo2 refresh failed", exc_info=True)
        except asyncio.CancelledError:
            return

    async def _release_spo2_for_hr(self) -> None:
        """Pause SpO₂ measurement so BLE heart-rate notifications resume."""
        if self._spo2_hr_released:
            return
        self._spo2_hr_released = True
        try:
            await self.set_spo2(False)
            self._spo2_holding = False
            await asyncio.sleep(0.35)
            if resolve_mode(self.stream_mode).hr_enable:
                await self._enable_heart_rate()
            # Keep last SpO₂ value on the ring/UI; mark sample as not actively measuring.
            if self.spo2 and self.spo2.spo2 > 0:
                held = BloodOxygen(enabled=False, spo2=self.spo2.spo2, on_wrist=self.spo2.on_wrist)
                self.spo2 = held
                self._events.emit("spo2", held)
        except Exception:
            self._spo2_hr_released = False
            log.debug("release spo2 for hr failed", exc_info=True)

    async def _cancel_realtime(self) -> None:
        self._realtime_on = False
        task = self._realtime_task
        self._realtime_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def get_raw_enabled(self) -> None:
        await self._write(pack(CMD_RAW, bytes([0])))

    async def get_sleep_history(self) -> None:
        await self._write(pack(CMD_GET_SLEEP, bytes([2])))

    async def get_sport_history(self) -> None:
        await self._write(pack(CMD_GET_SPORT_HISTORY, bytes([0])))

    async def get_health_history(self, begin_ms: int) -> None:
        await self._write(pack(CMD_GET_HEALTH_HISTORY, begin_utc_bytes(begin_ms)))

    async def get_heart_rate_history(self, begin_ms: int) -> None:
        await self._write(pack(CMD_GET_HR_HISTORY, begin_utc_bytes(begin_ms)))

    async def get_ppg_history(self, begin_ms: int) -> None:
        await self._write(pack(CMD_GET_PPG_HISTORY, begin_utc_bytes(begin_ms)))

    async def restore(self) -> None:
        await self._write(pack(CMD_RESTORE))

    async def enter_dfu(self) -> str:
        await self._write(pack_dfu())
        return increment_mac(self.address)

    async def _write(self, packet: bytes) -> None:
        if not self.client or not self.client.is_connected:
            raise RuntimeError("ring is not connected")
        async with self._lock:
            log.debug("tx %s", packet.hex())
            try:
                await self.client.write_gatt_char(UUID_FITNESS_TX, packet, response=True)
            except Exception:
                await self.client.write_gatt_char(UUID_FITNESS_TX, packet, response=False)

    async def _subscribe(self) -> None:
        assert self.client is not None
        await self.client.start_notify(UUID_FITNESS_RX, self._on_rx)
        await self.client.start_notify(UUID_HR_MEASUREMENT, self._on_heart_rate)
        try:
            await self.client.start_notify(UUID_BATTERY_LEVEL, self._on_battery)
        except Exception:
            log.debug("battery notify not available")

    async def _read_profile(self) -> None:
        assert self.client is not None
        mapping = {
            "system_id": UUID_DIS_SYSTEM,
            "model": UUID_DIS_MODEL,
            "serial": UUID_DIS_SERIAL,
            "firmware": UUID_DIS_FIRMWARE,
            "hardware": UUID_DIS_HARDWARE,
            "software": UUID_DIS_SOFTWARE,
            "vendor": UUID_DIS_VENDOR,
        }
        for key, uuid in mapping.items():
            try:
                value = await self.client.read_gatt_char(uuid)
                raw = bytes(value)
                self.info[key] = parse_system_id(raw) if key == "system_id" else brand_display(parse_ascii(raw))
            except Exception:
                continue
        try:
            battery = await self.client.read_gatt_char(UUID_BATTERY_LEVEL)
            self.battery = battery[0]
            self._events.emit("battery", self.battery)
        except Exception:
            pass
        if self.info:
            self._events.emit("info", self.info)

    def _on_disconnected(self, _client: BleakClient) -> None:
        self._events.emit("disconnected", self)

    def _on_rx(self, _char: BleakGATTCharacteristic, data: bytearray) -> None:
        for packet in take_frames(self._rx_buf, bytes(data)):
            log.debug("rx %s", packet.hex())
            try:
                events = parse_rx(packet)
            except Exception as exc:
                self._events.emit("error", exc, packet)
                continue
            for event in events:
                self._cache_event(event.name, event.payload)
                self._events.emit(event.name, event.payload, **event.extra)
                if event.name == "raw":
                    self._last_raw_at = time.monotonic()
                    self._events.emit("imu", event.payload.imu)
                    self._events.emit("ppg", event.payload.ppg)
                    self._estimate_hr_from_ppg(event.payload.ppg)
                elif event.name == "debug" and isinstance(event.payload, str):
                    self._note_optical_debug(event.payload)

    def _note_optical_debug(self, text: str) -> None:
        """Firmware SoftAdtGreen lines indicate SpO₂ contact before % is ready."""
        if not resolve_mode(self.stream_mode).spo2:
            return
        match = _SOFT_ADT_ONWRIST.search(text)
        if not match:
            return
        on_wrist = match.group(1) == "1"
        changed = self._optical_on_wrist is None or self._optical_on_wrist != on_wrist
        self._optical_on_wrist = on_wrist
        if changed:
            self._events.emit("optical_contact", on_wrist)
        current = self.spo2.spo2 if self.spo2 else 0
        # Surface measuring state even before mode 0x37 publishes a %.
        if current <= 0 and (changed or self.spo2 is None):
            sample = BloodOxygen(enabled=True, spo2=0, on_wrist=on_wrist)
            self.spo2 = sample
            self._events.emit("spo2", sample)

    def _cache_event(self, name: str, payload) -> None:
        if name == "sport":
            self.sport = payload
        elif name == "health":
            self.health = payload
        elif name == "temperature":
            self.temperature = payload
        elif name == "spo2":
            self.spo2 = payload
            if getattr(payload, "spo2", 0):
                self._last_spo2_at = time.monotonic()
                # Free the optical path for BLE HR once we have a reading.
                if (
                    resolve_mode(self.stream_mode).hr_enable
                    and self._spo2_holding
                    and not self._spo2_hr_released
                ):
                    try:
                        asyncio.get_running_loop().create_task(self._release_spo2_for_hr())
                    except RuntimeError:
                        pass
        elif name == "user_info":
            self.user = payload
        elif name == "raw":
            self.raw = payload
            self.imu = payload.imu
            self.ppg = payload.ppg
        elif name == "heart_rate":
            self.heart_rate = payload
        elif name == "heart_rate_history" and payload and self.heart_rate is None:
            last = payload[-1]
            if getattr(last, "bpm", 0):
                self.heart_rate = HeartRate(bpm=last.bpm)
                self._events.emit("heart_rate", self.heart_rate)

    def _estimate_hr_from_ppg(self, samples) -> None:
        if self.hr_source in {"ble", "off"} or not samples:
            return
        if self.hr_source == "auto" and time.monotonic() - self._ble_hr_at < 8.0:
            return
        estimated = self._ppg_hr.feed([sample.value for sample in samples], time.monotonic())
        if estimated is None:
            return
        self.heart_rate = estimated
        self._events.emit("heart_rate", estimated)

    def _on_heart_rate(self, _char: BleakGATTCharacteristic, data: bytearray) -> None:
        try:
            sample = parse_heart_rate(bytes(data))
        except Exception as exc:
            self._events.emit("error", exc, bytes(data))
            return
        if sample.bpm < 30 or self.hr_source in {"ppg", "off"}:
            return
        self._ble_hr_at = time.monotonic()
        self.heart_rate = sample
        self._events.emit("heart_rate", sample)
        hrv = self._hrv.feed(sample.rr_intervals)
        if hrv is not None:
            self.hrv = hrv
            self._events.emit("hrv", hrv)

    def _on_battery(self, _char: BleakGATTCharacteristic, data: bytearray) -> None:
        if data:
            self.battery = data[0]
            self._events.emit("battery", self.battery)


async def wait_until(predicate: Callable[[], bool], timeout: float = 8.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            raise TimeoutError("timed out waiting for ring data")
        await asyncio.sleep(0.05)


def run(coro: Awaitable[Any]) -> Any:
    return asyncio.run(coro)
