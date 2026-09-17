"""Test doubles for the Wi‑Fi drone host."""

from __future__ import annotations

from gadgetpanda.drone.protocol import StickState, build_stick_frame


class FakeDroneTransport:
    """In-memory UDP stand-in for unit tests."""

    def __init__(self) -> None:
        self.sent: list[bytes] = []
        self.is_connected = False
        self.host = "127.0.0.1"
        self.port = 7099

    async def connect(self, host: str, port: int, timeout: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.is_connected = True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def send(self, data: bytes) -> None:
        if not self.is_connected:
            raise RuntimeError("not connected")
        self.sent.append(bytes(data))

    @property
    def last_sent(self) -> bytes | None:
        return self.sent[-1] if self.sent else None


class SimulatedDrone:
    """Deterministic firmware stub that records stick frames."""

    def __init__(self, *, variant: str = "tc") -> None:
        self.variant = variant
        self.frames: list[bytes] = []
        self.state = StickState()

    def apply(self, state: StickState) -> bytes:
        self.state = state
        frame = build_stick_frame(state, variant=self.variant, udp_wrap=True)
        self.frames.append(frame)
        return frame
