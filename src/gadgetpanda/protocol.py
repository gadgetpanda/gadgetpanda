"""Gadget Panda frame codec.

See docs/protocol.md for the full specification.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from gadgetpanda.models import (
    Birthday,
    BloodOxygen,
    Health,
    HealthHistory,
    HeartRate,
    HeartRateHistory,
    PpgSample,
    Raw6D,
    RawFrame,
    SleepBlock,
    Sport,
    SportHistory,
    Temperature,
    UserInfo,
)

# GATT
UUID_HR_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
UUID_HR_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"
UUID_HR_CONTROL = "00002a39-0000-1000-8000-00805f9b34fb"
UUID_BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
UUID_BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"
UUID_DIS_SERVICE = "0000180a-0000-1000-8000-00805f9b34fb"
UUID_DIS_SYSTEM = "00002a23-0000-1000-8000-00805f9b34fb"
UUID_DIS_MODEL = "00002a24-0000-1000-8000-00805f9b34fb"
UUID_DIS_SERIAL = "00002a25-0000-1000-8000-00805f9b34fb"
UUID_DIS_FIRMWARE = "00002a26-0000-1000-8000-00805f9b34fb"
UUID_DIS_HARDWARE = "00002a27-0000-1000-8000-00805f9b34fb"
UUID_DIS_SOFTWARE = "00002a28-0000-1000-8000-00805f9b34fb"
UUID_DIS_VENDOR = "00002a29-0000-1000-8000-00805f9b34fb"
UUID_FITNESS_SERVICE = "aae28f00-71b5-42a1-8c3c-f9cf6ac969d0"
UUID_FITNESS_RX = "aae28f01-71b5-42a1-8c3c-f9cf6ac969d0"
UUID_FITNESS_TX = "aae28f02-71b5-42a1-8c3c-f9cf6ac969d0"

NAME_FILTERS = ("RING503PANDA", "RING503nPANDA", "CL")
_BLE_ADVERTISEMENT_ALIASES = {
    "RING503PANDA": ("RL503",),
    "RING503NPANDA": ("RL503N",),
}
END_TAG = 0xFFFFFFFF
SOF = 0xFF
CHK_XOR = 0x3A

CMD_GET_USER = 0x03
CMD_SET_USER = 0x04
CMD_GET_SLEEP = 0x05
CMD_SET_UTC = 0x08
CMD_SPORT_ON = 0x0D
CMD_GET_HEALTH = 0x13
CMD_GET_SPORT = 0x15
CMD_GET_SPORT_HISTORY = 0x16
CMD_DFU = 0x27
CMD_SET_SPO2 = 0x37
CMD_GET_TEMP = 0x38
CMD_SPORT_OFF = 0x74
CMD_GET_HEALTH_HISTORY = 0x91
CMD_GET_HR_HISTORY = 0x92
CMD_PPG_HISTORY_END = 0x93
CMD_GET_PPG_HISTORY = 0x94
CMD_SET_BIRTHDAY = 0x96
CMD_GET_BIRTHDAY = 0x97
CMD_RAW = 0x98
CMD_RESTORE = 0xF3

RX_RAW_STREAM = 0x99


def signed_sum(data: bytes) -> int:
    total = 0
    for byte in data:
        total += byte - 256 if byte > 127 else byte
    return total


def checksum(data: bytes) -> int:
    return ((-signed_sum(data)) ^ CHK_XOR) & 0xFF


def pack(cmd: int, payload: bytes = b"") -> bytes:
    body = bytes([SOF, 4 + len(payload), cmd & 0xFF]) + payload
    return body + bytes([checksum(body)])


def pack_dfu() -> bytes:
    stub = bytes([SOF, 4, CMD_DFU, 0x00])
    return bytes([SOF, 4, CMD_DFU, checksum(stub)])


def u8(data: bytes, offset: int) -> int:
    return data[offset]


def u16be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def u24be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 3], "big")


def u32be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def u40be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 5], "big")


def i16be(data: bytes, offset: int) -> int:
    return struct.unpack_from(">h", data, offset)[0]


def _local_tz():
    return datetime.now().astimezone().tzinfo or timezone.utc


def utc_seconds(when: datetime | None = None, tz: ZoneInfo | None = None) -> int:
    """Zone-adjusted unix seconds, matching the ring DateUtil.getZoneUTC clock."""
    zone = tz or _local_tz()
    now = when.astimezone(zone) if when else datetime.now(zone)
    offset = now.utcoffset() or timedelta(0)
    return int(now.timestamp() + offset.total_seconds())


def restore_zone_utc(stamp_sec: int, tz: ZoneInfo | None = None) -> int:
    """Return epoch milliseconds, matching DateUtil.restoreZoneUTC."""
    zone = tz or _local_tz()
    offset = datetime.fromtimestamp(stamp_sec, tz=zone).utcoffset() or timedelta(0)
    return int(stamp_sec * 1000 - offset.total_seconds() * 1000)


def utc_bytes(when: datetime | None = None) -> bytes:
    return utc_seconds(when).to_bytes(4, "big")


def begin_utc_bytes(begin_ms: int) -> bytes:
    dt = datetime.fromtimestamp(begin_ms / 1000, tz=datetime.now().astimezone().tzinfo)
    return utc_seconds(dt).to_bytes(4, "big")


def increment_mac(address: str) -> str:
    parts = address.split(":")
    last = (int(parts[-1], 16) + 1) & 0xFF
    parts[-1] = f"{last:02X}"
    return ":".join(parts)


def looks_like_ring(name: str | None, filters: tuple[str, ...] = NAME_FILTERS) -> bool:
    if not name:
        return False
    upper = name.upper()
    for token in filters:
        key = token.upper()
        if key in upper:
            return True
        if any(alias.upper() in upper for alias in _BLE_ADVERTISEMENT_ALIASES.get(key, ())):
            return True
    return False


def parse_heart_rate(data: bytes) -> HeartRate:
    if len(data) < 2:
        raise ValueError("heart rate packet too short")
    flags = data[0]
    hr_16 = flags & 1
    contact_bits = (flags >> 1) & 0x3
    contact: bool | None
    if contact_bits in (2, 3):
        contact = contact_bits == 3
    else:
        contact = None
    energy_present = bool(flags & 0x08)
    rr_present = bool(flags & 0x10)
    offset = 1
    if hr_16:
        bpm = int.from_bytes(data[offset : offset + 2], "little")
        offset += 2
    else:
        bpm = data[offset]
        offset += 1
    energy = None
    if energy_present:
        energy = int.from_bytes(data[offset : offset + 2], "little")
        offset += 2
    rr: list[int] = []
    if rr_present:
        while offset + 2 <= len(data):
            rr.append(int.from_bytes(data[offset : offset + 2], "little"))
            offset += 2
    return HeartRate(bpm=bpm, contact=contact, rr_intervals=tuple(rr), energy_kj=energy)


def parse_ascii(data: bytes) -> str:
    return bytes(b for b in data if b).decode("ascii", errors="ignore").strip()


def parse_system_id(data: bytes) -> str:
    return bytes(data).hex()


@dataclass
class RxEvent:
    name: str
    payload: Any
    extra: dict[str, Any]


def take_frames(buffer: bytearray, data: bytes, max_buf: int = 4096) -> list[bytes]:
    """Reassemble SOF/LEN frames from one or more BLE notifications."""
    buffer.extend(data)
    if len(buffer) > max_buf:
        del buffer[:-max_buf]
    frames: list[bytes] = []
    while len(buffer) >= 4:
        if buffer[0] != SOF:
            try:
                start = buffer.index(SOF, 1)
            except ValueError:
                buffer.clear()
                break
            del buffer[:start]
            continue
        declared = buffer[1]
        if declared < 4:
            del buffer[0]
            continue
        if len(buffer) < declared:
            break
        frames.append(bytes(buffer[:declared]))
        del buffer[:declared]
    return frames


def parse_rx(packet: bytes) -> list[RxEvent]:
    if len(packet) < 4 or packet[0] != SOF:
        return []
    declared = packet[1]
    if declared < 4:
        return []
    if len(packet) < declared:
        return []
    packet = packet[:declared]
    mode = packet[2]
    parser = RX_PARSERS.get(mode)
    if parser is None:
        return [RxEvent("raw_command", packet, {"mode": mode})]
    result = parser(packet)
    if result is None:
        return []
    if isinstance(result, list):
        return result
    return [result]


def _user(packet: bytes) -> RxEvent:
    return RxEvent(
        "user_info",
        UserInfo(
            age=u8(packet, 5),
            sex=u8(packet, 6),
            weight_kg=u8(packet, 7),
            height_cm=u8(packet, 8),
            user_id=u40be(packet, 9),
        ),
        {},
    )


def _sleep(packet: bytes) -> list[RxEvent] | None:
    sub = u8(packet, 3)
    if sub == 0xFF:
        return [RxEvent("sleep_history_complete", None, {})]
    if sub != 0x03:
        return None
    blocks: list[SleepBlock] = []
    index = 4
    while index < len(packet) - 1:
        count = packet[index]
        if count < 1 or index + 5 + count > len(packet):
            break
        utc = u32be(packet, index + 1)
        actions = tuple(packet[index + 5 : index + 5 + count])
        blocks.append(SleepBlock(stamp_ms=restore_zone_utc(utc), actions=actions))
        index += 5 + count
    return [RxEvent("sleep_history_chunk", tuple(blocks), {})] if blocks else None


def _health(packet: bytes) -> RxEvent:
    return RxEvent(
        "health",
        Health(
            vo2max=u8(packet, 3),
            breath_rate=u8(packet, 4),
            emotion=u8(packet, 5),
            stress=u8(packet, 6),
            stamina=u8(packet, 7),
        ),
        {},
    )


def _sport(packet: bytes) -> RxEvent:
    return RxEvent(
        "sport",
        Sport(
            steps=u24be(packet, 3),
            distance_m=u24be(packet, 6) / 100.0,
            calories_kcal=u24be(packet, 9) / 10.0,
        ),
        {},
    )


def _sport_history(packet: bytes) -> RxEvent:
    body = packet[3:-1]
    rows: list[SportHistory] = []
    for offset in range(0, len(body) // 10 * 10, 10):
        rows.append(
            SportHistory(
                stamp_ms=restore_zone_utc(u32be(body, offset)),
                steps=u24be(body, offset + 4),
                calories=u24be(body, offset + 7),
            )
        )
    rows.reverse()
    return RxEvent("sport_history", tuple(rows), {})


def _spo2(packet: bytes) -> RxEvent | None:
    if packet[1] < 5:
        return RxEvent("spo2", BloodOxygen(enabled=False, spo2=0, on_wrist=False), {})
    if packet[1] < 8:
        return RxEvent(
            "spo2",
            BloodOxygen(enabled=u8(packet, 3) == 1, spo2=0, on_wrist=False),
            {},
        )
    return RxEvent(
        "spo2",
        BloodOxygen(
            enabled=u8(packet, 3) == 1,
            spo2=u8(packet, 4),
            on_wrist=u8(packet, 7) == 1,
        ),
        {},
    )


def _temperature(packet: bytes) -> RxEvent:
    return RxEvent(
        "temperature",
        Temperature(
            ambient_c=u16be(packet, 3) / 10.0,
            wrist_c=u16be(packet, 5) / 10.0,
            body_c=u16be(packet, 7) / 10.0,
        ),
        {},
    )


def _health_history(packet: bytes) -> list[RxEvent]:
    tag = u32be(packet, 3)
    if tag == END_TAG:
        return [RxEvent("health_history_complete", None, {})]
    body = packet[3:-1]
    events: list[RxEvent] = []
    for offset in range(0, len(body) // 18 * 18, 18):
        events.append(
            RxEvent(
                "health_history",
                HealthHistory(
                    start=u32be(body, offset),
                    stamp_ms=restore_zone_utc(u32be(body, offset + 4)),
                    type=u8(body, offset + 8),
                    stress=u8(body, offset + 9),
                    breath_rate=u8(body, offset + 10),
                    vo2max=u8(body, offset + 11),
                    emotion=u8(body, offset + 12),
                    stamina=u8(body, offset + 13),
                    heart_rate=u8(body, offset + 14),
                    spo2=u8(body, offset + 15),
                    temperature_c=u16be(body, offset + 16) / 10.0,
                ),
                {},
            )
        )
    return events


def _hr_history(packet: bytes) -> list[RxEvent]:
    total = u16be(packet, 3)
    progress = u16be(packet, 5)
    body = packet[7:-1]
    rows: list[HeartRateHistory] = []
    for offset in range(0, len(body) // 5 * 5, 5):
        rows.append(
            HeartRateHistory(
                stamp_ms=restore_zone_utc(u32be(body, offset)),
                bpm=u8(body, offset + 4),
                progress=progress,
                total=total,
            )
        )
    events = [RxEvent("heart_rate_history", tuple(rows), {"progress": progress, "total": total})]
    if progress == total:
        events.append(RxEvent("heart_rate_history_complete", None, {}))
    return events


def _birthday(packet: bytes) -> RxEvent:
    return RxEvent(
        "birthday",
        Birthday(year=u16be(packet, 3), month=u8(packet, 5), day=u8(packet, 6)),
        {},
    )


def _utc_ack(_packet: bytes) -> RxEvent:
    return RxEvent("utc", True, {})


def _firmware_debug(packet: bytes) -> RxEvent:
    text = bytes(byte for byte in packet[3:-1] if 32 <= byte < 127).decode("ascii", errors="ignore").strip()
    return RxEvent("debug", text, {"mode": packet[2]})


def _ppg_history(packet: bytes) -> list[RxEvent]:
    tag = u32be(packet, 3)
    if tag == END_TAG:
        return [RxEvent("ppg_history_complete", None, {})]
    total = u16be(packet, 3)
    progress = u16be(packet, 5)
    body = packet[7:-1]
    rows = []
    for offset in range(0, len(body) // 62 * 62, 62):
        stamp_ms = restore_zone_utc(u32be(body, offset))
        is_wear = u8(body, offset + 4) == 1
        slots = body[offset + 5 : offset + 62]
        parsed_slots = []
        for slot_off in range(0, len(slots) // 19 * 19, 19):
            parsed_slots.append(
                {
                    "min_current": u8(slots, slot_off),
                    "max_current": u8(slots, slot_off + 1),
                    "min_pd0": u32be(slots, slot_off + 2),
                    "min_pd1": u32be(slots, slot_off + 6),
                    "max_pd0": u32be(slots, slot_off + 10),
                    "max_pd1": u32be(slots, slot_off + 14),
                    "tia_gain": u8(slots, slot_off + 18),
                }
            )
        rows.append({"stamp_ms": stamp_ms, "is_wear": is_wear, "slots": parsed_slots})
    events = [RxEvent("ppg_history", tuple(rows), {"progress": progress, "total": total})]
    if progress == total:
        events.append(RxEvent("ppg_history_complete", None, {}))
    return events


def _raw_status(packet: bytes) -> RxEvent:
    return RxEvent("raw_status", u8(packet, 4) == 1, {})


def _raw_stream(packet: bytes) -> RxEvent:
    frame = u8(packet, 3)
    stamp = u32be(packet, 4)
    n6d = u8(packet, 8)
    imu_bytes = packet[9 : 9 + n6d] if n6d else b""
    nppg = u8(packet, 9 + n6d) if len(packet) > 9 + n6d else 0
    flag = u8(packet, 10 + n6d) if len(packet) > 10 + n6d else 0
    ppg_bytes = packet[11 + n6d : 11 + n6d + nppg] if nppg else b""
    imu = tuple(
        Raw6D(
            acc_x=i16be(imu_bytes, offset),
            acc_y=i16be(imu_bytes, offset + 2),
            acc_z=i16be(imu_bytes, offset + 4),
            gyro_x=i16be(imu_bytes, offset + 6),
            gyro_y=i16be(imu_bytes, offset + 8),
            gyro_z=i16be(imu_bytes, offset + 10),
        )
        for offset in range(0, len(imu_bytes) // 12 * 12, 12)
    )
    ppg = tuple(
        PpgSample(flag=flag, value=u24be(ppg_bytes, offset))
        for offset in range(0, len(ppg_bytes) // 3 * 3, 3)
    )
    return RxEvent("raw", RawFrame(frame=frame, stamp=stamp, imu=imu, ppg=ppg), {})


RX_PARSERS = {
    CMD_SET_UTC: _utc_ack,
    CMD_GET_USER: _user,
    CMD_GET_SLEEP: _sleep,
    CMD_GET_HEALTH: _health,
    CMD_GET_SPORT: _sport,
    CMD_GET_SPORT_HISTORY: _sport_history,
    CMD_SET_SPO2: _spo2,
    CMD_GET_TEMP: _temperature,
    CMD_SPORT_ON: lambda packet: RxEvent("sport_mode", True, {}),
    CMD_SPORT_OFF: lambda packet: RxEvent("sport_mode", False, {}),
    0x47: _firmware_debug,
    CMD_GET_HEALTH_HISTORY: _health_history,
    CMD_GET_HR_HISTORY: _hr_history,
    CMD_PPG_HISTORY_END: _ppg_history,
    CMD_GET_PPG_HISTORY: _ppg_history,
    CMD_GET_BIRTHDAY: _birthday,
    CMD_RAW: _raw_status,
    RX_RAW_STREAM: _raw_stream,
}
