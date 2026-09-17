"""In-process ring simulator for end-to-end tests."""

from __future__ import annotations

from typing import Any, Callable

from gadgetpanda.models import AdvertisedRing, oem_vendor_mark
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
    CMD_SET_USER,
    CMD_RAW,
    CMD_SET_SPO2,
    END_TAG,
    RX_RAW_STREAM,
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
    UUID_HR_MEASUREMENT,
    pack,
)


def _uuid(value: Any) -> str:
    return str(value).lower()


class SimulatedRing:
    """Responds to Gadget Panda TX frames with protocol-correct RX packets."""

    def __init__(self, address: str = "AA:BB:CC:DD:EE:10", name: str = "RL503-E2E"):
        self.address = address
        self.name = name
        self.rssi = -48
        self.raw_enabled = False
        self.tx_log: list[bytes] = []
        self.user = {"age": 28, "sex": 1, "weight_kg": 70, "height_cm": 175, "user_id": 81}
        self._notify: dict[str, Callable] = {}
        self.profile = {
            UUID_DIS_SYSTEM: b"GP-SYS",
            UUID_DIS_MODEL: b"RL503",
            UUID_DIS_SERIAL: b"GP0001",
            UUID_DIS_FIRMWARE: b"1.0.4",
            UUID_DIS_HARDWARE: b"A1",
            UUID_DIS_SOFTWARE: b"1.0.4",
            UUID_DIS_VENDOR: oem_vendor_mark().encode("ascii"),
            UUID_BATTERY_LEVEL: bytes([87]),
        }

    def advertised(self) -> AdvertisedRing:
        return AdvertisedRing(name=self.name, address=self.address, rssi=self.rssi)

    def attach(self, notify: dict[str, Callable]) -> None:
        self._notify = notify

    def read(self, uuid: str) -> bytes:
        key = _uuid(uuid)
        if key not in self.profile:
            raise KeyError(key)
        return self.profile[key]

    def notify(self, uuid: str, data: bytes) -> None:
        callback = self._notify.get(_uuid(uuid))
        if callback:
            callback(None, bytearray(data))

    def push_heart_rate(self, bpm: int, rr: tuple[int, ...] = ()) -> None:
        flags = 0x10 if rr else 0x00
        payload = bytearray([flags, bpm & 0xFF])
        for interval in rr:
            payload.extend(int(interval).to_bytes(2, "little"))
        self.notify(UUID_HR_MEASUREMENT, bytes(payload))

    def push_battery(self, level: int) -> None:
        self.profile[UUID_BATTERY_LEVEL] = bytes([level & 0xFF])
        self.notify(UUID_BATTERY_LEVEL, bytes([level & 0xFF]))

    def write(self, uuid: str, packet: bytes) -> None:
        if _uuid(uuid) != UUID_FITNESS_TX:
            return
        self.tx_log.append(packet)
        if len(packet) < 3:
            return
        cmd = packet[2]
        handler = self._handlers.get(cmd)
        if handler:
            handler(self, packet)

    def _handle_sport(self, _packet: bytes) -> None:
        payload = (1840).to_bytes(3, "big") + (12500).to_bytes(3, "big") + (37).to_bytes(3, "big")
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_SPORT, payload))

    def _handle_health(self, _packet: bytes) -> None:
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_HEALTH, bytes([42, 16, 3, 4, 80])))

    def _handle_temp(self, _packet: bytes) -> None:
        payload = (265).to_bytes(2, "big") + (312).to_bytes(2, "big") + (366).to_bytes(2, "big")
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_TEMP, payload))

    def _user_payload(self) -> bytes:
        user = self.user
        return bytes([0, 0, user["age"], user["sex"], user["weight_kg"], user["height_cm"]]) + user["user_id"].to_bytes(5, "big")

    def _handle_user(self, _packet: bytes) -> None:
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_USER, self._user_payload()))

    def _handle_set_user(self, packet: bytes) -> None:
        if len(packet) >= 12:
            self.user = {
                "age": packet[3],
                "sex": packet[4],
                "weight_kg": packet[5],
                "height_cm": packet[6],
                "user_id": int.from_bytes(packet[7:12], "big"),
            }
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_USER, self._user_payload()))

    def _handle_birthday(self, _packet: bytes) -> None:
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_BIRTHDAY, (1998).to_bytes(2, "big") + bytes([5, 20])))

    def _handle_spo2(self, packet: bytes) -> None:
        enabled = packet[3] == 1 if len(packet) > 3 else 0
        self.notify(UUID_FITNESS_RX, pack(CMD_SET_SPO2, bytes([enabled, 98, 0, 0, 1])))

    def _handle_raw(self, packet: bytes) -> None:
        if len(packet) >= 5 and packet[3] == 1:
            self.raw_enabled = packet[4] == 1
        status = bytes([0, 1 if self.raw_enabled else 0])
        self.notify(UUID_FITNESS_RX, pack(CMD_RAW, status))
        if self.raw_enabled:
            imu = (400).to_bytes(2, "big", signed=True) * 3 + (0).to_bytes(2, "big", signed=True) * 3
            ppg = (1200).to_bytes(3, "big")
            payload = bytes([3]) + (10).to_bytes(4, "big") + bytes([12]) + imu + bytes([3, 1]) + ppg
            self.notify(UUID_FITNESS_RX, pack(RX_RAW_STREAM, payload))

    def _handle_sport_history(self, _packet: bytes) -> None:
        record = (1_700_000_000).to_bytes(4, "big") + (900).to_bytes(3, "big") + (40).to_bytes(3, "big")
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_SPORT_HISTORY, record))

    def _handle_sleep(self, _packet: bytes) -> None:
        block = bytes([3, 2]) + (1_700_000_000).to_bytes(4, "big") + bytes([8, 25])
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_SLEEP, block))
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_SLEEP, bytes([0xFF])))

    def _handle_health_history(self, _packet: bytes) -> None:
        record = (
            (1_700_000_000).to_bytes(4, "big")
            + (1_700_000_600).to_bytes(4, "big")
            + bytes([1, 3, 15, 40, 2, 70, 72, 97])
            + (366).to_bytes(2, "big")
        )
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_HEALTH_HISTORY, record))
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_HEALTH_HISTORY, END_TAG.to_bytes(4, "big")))

    def _handle_hr_history(self, _packet: bytes) -> None:
        payload = (1).to_bytes(2, "big") + (1).to_bytes(2, "big") + (1_700_000_000).to_bytes(4, "big") + bytes([74])
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_HR_HISTORY, payload))

    def _handle_ppg_history(self, _packet: bytes) -> None:
        self.notify(UUID_FITNESS_RX, pack(CMD_GET_PPG_HISTORY, END_TAG.to_bytes(4, "big")))

    _handlers = {
        CMD_GET_SPORT: _handle_sport,
        CMD_GET_HEALTH: _handle_health,
        CMD_GET_TEMP: _handle_temp,
        CMD_GET_USER: _handle_user,
        CMD_SET_USER: _handle_set_user,
        CMD_GET_BIRTHDAY: _handle_birthday,
        CMD_SET_SPO2: _handle_spo2,
        CMD_RAW: _handle_raw,
        CMD_GET_SPORT_HISTORY: _handle_sport_history,
        CMD_GET_SLEEP: _handle_sleep,
        CMD_GET_HEALTH_HISTORY: _handle_health_history,
        CMD_GET_HR_HISTORY: _handle_hr_history,
        CMD_GET_PPG_HISTORY: _handle_ppg_history,
    }


class FakeBleClient:
    """Bleak-shaped transport backed by SimulatedRing."""

    def __init__(self, firmware: SimulatedRing):
        self.firmware = firmware
        self.address = firmware.address
        self._connected = False
        self._notify: dict[str, Callable] = {}

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True
        self.firmware.attach(self._notify)

    async def request_mtu(self, mtu: int) -> int:
        return mtu

    async def disconnect(self) -> None:
        self._connected = False

    async def read_gatt_char(self, uuid: Any) -> bytes:
        return self.firmware.read(uuid)

    async def write_gatt_char(self, uuid: Any, data: bytes, response: bool = True) -> None:
        self.firmware.write(uuid, bytes(data))

    async def start_notify(self, uuid: Any, callback: Callable) -> None:
        self._notify[_uuid(uuid)] = callback
        self.firmware.attach(self._notify)
