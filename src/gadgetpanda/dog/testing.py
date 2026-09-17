"""In-process dog simulator for unit / e2e tests."""

from __future__ import annotations

from typing import Any, Callable

from gadgetpanda.dog.models import AdvertisedDog
from gadgetpanda.dog.protocol import UUID_NOTIFY, UUID_WRITE


def _uuid(value: Any) -> str:
    return str(value).lower()


class SimulatedDog:
    """Records GATT writes and can push notify payloads."""

    def __init__(self, address: str = "AA:BB:CC:DD:EE:D0", name: str = "X1-TEST"):
        self.address = address
        self.name = name
        self.rssi = -50
        self.tx_log: list[bytes] = []
        self._notify: dict[str, Callable] = {}

    def advertised(self) -> AdvertisedDog:
        return AdvertisedDog(name=self.name, address=self.address, rssi=self.rssi)

    def attach(self, notify: dict[str, Callable]) -> None:
        self._notify = notify

    def notify(self, uuid: str, data: bytes) -> None:
        callback = self._notify.get(_uuid(uuid))
        if callback:
            callback(None, bytearray(data))

    def push_rx(self, data: bytes) -> None:
        self.notify(UUID_NOTIFY, data)

    def write(self, uuid: str, packet: bytes) -> None:
        if _uuid(uuid) != UUID_WRITE:
            return
        self.tx_log.append(packet)


class FakeDogBleClient:
    """Bleak-shaped transport backed by SimulatedDog."""

    def __init__(self, firmware: SimulatedDog):
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

    async def disconnect(self) -> None:
        self._connected = False

    async def write_gatt_char(self, uuid: Any, data: bytes, response: bool = True) -> None:
        self.firmware.write(uuid, bytes(data))

    async def start_notify(self, uuid: Any, callback: Callable) -> None:
        self._notify[_uuid(uuid)] = callback
        self.firmware.attach(self._notify)
