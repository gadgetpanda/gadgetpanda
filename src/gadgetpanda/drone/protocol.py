"""Clean-room V66 / KY UFO style UDP frames.

Host talks to ``192.168.1.1:7099``:

* heartbeat ``01 01`` every ~1s
* stick frames prefixed with ``03`` then body starting ``66`` … ending ``99``
* TC (short) body: 8 bytes
* GL (long) body: 20 bytes (``66 14 … 99``)
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_HOST = "192.168.1.1"
DEFAULT_UDP_PORT = 7099
DEFAULT_RTSP = "rtsp://192.168.1.1:7070/webcam"
CENTER = 128
MIN_AXIS = 1
MAX_AXIS = 255
SEND_INTERVAL_S = 0.05
HEARTBEAT_INTERVAL_S = 1.0

FRAME_PREFIX = 0x03
FRAME_HEAD = 0x66
FRAME_TAIL = 0x99
GL_MARKER = 0x14

HEARTBEAT = bytes([0x01, 0x01])
STOP_CONTROL = bytes([0x08, 0x01])
SWITCH_CAMERA_FRONT = bytes([0x06, 0x01])
SWITCH_CAMERA_BACK = bytes([0x06, 0x02])


@dataclass(frozen=True)
class StickState:
    """Axis values and latched flag bits for one control tick."""

    roll: int = CENTER  # controlByte1
    pitch: int = CENTER  # controlByte2
    throttle: int = CENTER
    yaw: int = CENTER
    takeoff: bool = False
    land: bool = False
    emergency: bool = False
    circle: bool = False
    headless: bool = False
    unlock_or_return: bool = False
    light: bool = False
    calibrate: bool = False
    gesture: bool = False
    fixed_height: bool = False

    def clamp(self) -> StickState:
        def axis(value: int) -> int:
            return max(MIN_AXIS, min(MAX_AXIS, int(value)))

        throttle = int(self.throttle)
        if throttle == MIN_AXIS:
            throttle = 0
        return StickState(
            roll=axis(self.roll),
            pitch=axis(self.pitch),
            throttle=max(0, min(MAX_AXIS, throttle)),
            yaw=axis(self.yaw),
            takeoff=self.takeoff,
            land=self.land,
            emergency=self.emergency,
            circle=self.circle,
            headless=self.headless,
            unlock_or_return=self.unlock_or_return,
            light=self.light,
            calibrate=self.calibrate,
            gesture=self.gesture,
            fixed_height=self.fixed_height,
        )


def clamp_axis(value: int) -> int:
    return max(MIN_AXIS, min(MAX_AXIS, int(value)))


def tc_flags(state: StickState) -> int:
    flags = 0
    if state.takeoff:
        flags += 1
    if state.land:
        flags += 2
    if state.emergency:
        flags += 4
    if state.circle:
        flags += 8
    if state.headless:
        flags += 16
    if state.unlock_or_return:
        flags += 32
    if state.light:
        flags += 64
    if state.calibrate:
        flags += 128
    return flags & 0xFF


def gl_flag_bytes(state: StickState) -> tuple[int, int]:
    flag1 = 0
    if state.takeoff or state.land:
        flag1 += 1
    if state.emergency:
        flag1 += 2
    if state.calibrate:
        flag1 += 4
    if state.circle:
        flag1 += 8
    if state.light:
        flag1 += 16
    if state.gesture:
        flag1 += 64
    flag2 = 0
    if state.headless:
        flag2 += 1
    if state.fixed_height:
        flag2 += 2
    return flag1 & 0xFF, flag2 & 0xFF


def build_tc_body(state: StickState) -> bytes:
    s = state.clamp()
    flags = tc_flags(s)
    checksum = s.roll ^ s.pitch ^ s.throttle ^ s.yaw ^ flags
    return bytes(
        [
            FRAME_HEAD,
            s.roll,
            s.pitch,
            s.throttle,
            s.yaw,
            flags,
            checksum & 0xFF,
            FRAME_TAIL,
        ]
    )


def build_gl_body(state: StickState) -> bytes:
    s = state.clamp()
    flag1, flag2 = gl_flag_bytes(s)
    checksum = s.roll ^ s.pitch ^ s.throttle ^ s.yaw ^ flag1 ^ flag2
    return bytes(
        [
            FRAME_HEAD,
            GL_MARKER,
            s.roll,
            s.pitch,
            s.throttle,
            s.yaw,
            flag1,
            flag2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            checksum & 0xFF,
            FRAME_TAIL,
        ]
    )


def build_stick_frame(state: StickState, *, variant: str = "tc", udp_wrap: bool = True) -> bytes:
    body = build_gl_body(state) if variant == "gl" else build_tc_body(state)
    return wrap_udp(body) if udp_wrap else body


def wrap_udp(body: bytes) -> bytes:
    return bytes([FRAME_PREFIX]) + body


def parse_hex_payload(data: bytes | str) -> bytes:
    if isinstance(data, bytes):
        return data
    cleaned = data.replace(" ", "").replace(":", "").strip()
    if not cleaned:
        raise ValueError("empty hex")
    if len(cleaned) % 2:
        raise ValueError("odd hex length")
    return bytes.fromhex(cleaned)
