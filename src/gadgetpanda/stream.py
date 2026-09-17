from __future__ import annotations

from dataclasses import dataclass


CORE_EVENTS = frozenset({"status", "connected", "disconnected", "info", "user", "user_status", "battery", "mode"})


@dataclass(frozen=True)
class StreamMode:
    id: str
    label: str
    en: str
    hint: str
    hr: str
    raw: bool
    spo2: bool
    poll: bool
    sport_mode: bool
    hr_enable: bool
    sections: tuple[str, ...]
    events: frozenset[str]
    gets: tuple[str, ...] = ()
    needs: tuple[str, ...] = ()
    skips: tuple[str, ...] = ()


MODES: dict[str, StreamMode] = {
    "all": StreamMode(
        id="all",
        label="ทั้งหมด",
        en="All",
        hint="สตรีมหลักสำหรับ Maker — PPG/IMU + ชีพจร + กีฬา/สุขภาพ",
        hr="auto",
        raw=True,
        spo2=False,
        poll=True,
        sport_mode=True,
        hr_enable=True,
        sections=("vitals", "temperature", "activity", "wellness", "motion", "optical"),
        events=frozenset(),
        gets=(
            "ชีพจร BLE (หรือประมาณจาก PPG)",
            "HRV จาก RR",
            "คลื่น PPG",
            "Acc / Gyro (IMU)",
            "อุณหภูมิ",
            "ก้าว · ระยะ · แคลอรี่",
            "Stress · VO₂ · หายใจ · อารมณ์ · ความทน",
            "แบตเตอรี่",
        ),
        needs=(
            "สวมแหวนให้ LED ชิดผิว",
            "รอ ~2 วินาทีหลังเปิดโหมดให้ raw เริ่ม",
            "BLE ต่อค้าง (อย่าปิด Bluetooth)",
        ),
        skips=(
            "SpO₂ — ใช้โหมดสัญญาณชีพ (เซ็นเซอร์แสงใช้ร่วมกับ PPG ไม่ได้)",
        ),
    ),
    "hr": StreamMode(
        id="hr",
        label="ชีพจร BLE",
        en="Heart rate",
        hint="เฉพาะ Heart Rate Service — ไม่เปิด PPG/IMU/SpO₂",
        hr="ble",
        raw=False,
        spo2=False,
        poll=False,
        sport_mode=False,
        hr_enable=True,
        sections=("vitals",),
        events=frozenset({"heart_rate", "hrv"}),
        gets=("ชีพจร BPM จาก BLE 0x2A37", "HRV (SDNN) คำนวณจาก RR ฝั่งโฮสต์", "แบตเตอรี่"),
        needs=("สวมแหวน", "เปิด notify Heart Rate ของแหวน"),
        skips=("PPG", "IMU", "SpO₂", "ก้าว/สุขภาพโพล"),
    ),
    "ppg": StreamMode(
        id="ppg",
        label="PPG + ชีพจร",
        en="Optical",
        hint="คลื่นแสงดิบ + ประมาณชีพจรจาก PPG — ไม่วัด SpO₂",
        hr="ppg",
        raw=True,
        spo2=False,
        poll=False,
        sport_mode=True,
        hr_enable=False,
        sections=("vitals", "optical", "motion"),
        events=frozenset({"ppg", "imu", "heart_rate"}),
        gets=("คลื่น PPG realtime", "Acc / Gyro", "ชีพจรประมาณจาก PPG"),
        needs=(
            "สวมแน่น LED ชิดผิว",
            "รอ ~2 วินาทีให้สตรีม 0x99 เริ่ม",
            "นิ่งพอสมควรถ้าต้องการคลื่นสวย",
        ),
        skips=("SpO₂", "HRV จาก BLE RR", "ก้าว/สุขภาพโพล"),
    ),
    "vitals": StreamMode(
        id="vitals",
        label="สัญญาณชีพ",
        en="Vitals",
        hint="เน้น SpO₂ + ชีพจร BLE + อุณหภูมิ/สุขภาพ — ไม่เปิด PPG raw",
        hr="ble",
        raw=False,
        spo2=True,
        poll=True,
        sport_mode=False,
        hr_enable=True,
        sections=("vitals", "temperature", "wellness"),
        events=frozenset({"heart_rate", "hrv", "spo2", "temperature", "health", "optical_contact"}),
        gets=(
            "SpO₂ %",
            "ชีพจร BLE + HRV (หลังได้ SpO₂ แล้วระบบจะคืนชีพจร)",
            "อุณหภูมิ body / wrist / ambient",
            "Stress · VO₂ · หายใจ · อารมณ์ · ความทน",
            "แบตเตอรี่",
        ),
        needs=(
            "สวมแน่นมาก · นิ้วอยู่นิ่ง 15–40 วินาที",
            "อย่าเปิดโหมด PPG พร้อมกัน (LED ใช้ร่วมกัน)",
            "ได้ % แล้วระบบพัก SpO₂ ชั่วคราวเพื่อดึงชีพจร · วัดซ้ำ ~90 วินาที",
        ),
        skips=("คลื่น PPG", "Acc / Gyro", "ก้าว/ระยะ"),
    ),
    "motion": StreamMode(
        id="motion",
        label="การเคลื่อนไหว",
        en="IMU",
        hint="เฉพาะ Acc / Gyro สำหรับ gesture / โมชัน",
        hr="off",
        raw=True,
        spo2=False,
        poll=False,
        sport_mode=True,
        hr_enable=False,
        sections=("motion",),
        events=frozenset({"imu"}),
        gets=("Accelerometer X/Y/Z", "Gyroscope X/Y/Z"),
        needs=("รอ ~2 วินาทีหลังเปิดโหมด", "ขยับนิ้ว/มือเพื่อเห็นกราฟ"),
        skips=("ชีพจร", "PPG waveform", "SpO₂", "กีฬา/สุขภาพ"),
    ),
    "activity": StreamMode(
        id="activity",
        label="กิจกรรม",
        en="Activity",
        hint="โพลค่าสะสมจากแหวน — ไม่สตรีมเซ็นเซอร์ดิบ",
        hr="off",
        raw=False,
        spo2=False,
        poll=True,
        sport_mode=False,
        hr_enable=False,
        sections=("activity", "wellness", "temperature"),
        events=frozenset({"sport", "health", "temperature"}),
        gets=("ก้าว · ระยะทาง · แคลอรี่", "ค่าสุขภาพโพลได้", "อุณหภูมิ"),
        needs=("แหวนเคยซิงก์กิจกรรมมาก่อน", "โพลทุก ~1–2 วินาที"),
        skips=("PPG", "IMU", "SpO₂", "ชีพจร realtime"),
    ),
}

DEFAULT_MODE = "all"


def resolve_mode(name: str | None) -> StreamMode:
    return MODES.get(name or "", MODES[DEFAULT_MODE])


def allows_event(mode: str, event: str) -> bool:
    spec = resolve_mode(mode)
    if event in CORE_EVENTS:
        return True
    if not spec.events:
        return True
    return event in spec.events


def _mode_card(item: StreamMode) -> dict:
    return {
        "id": item.id,
        "label": item.label,
        "en": item.en,
        "hint": item.hint,
        "gets": list(item.gets),
        "needs": list(item.needs),
        "skips": list(item.skips),
        "flags": {
            "raw": item.raw,
            "spo2": item.spo2,
            "hr": item.hr,
            "poll": item.poll,
        },
    }


def mode_payload(mode: str | None = None) -> dict:
    spec = resolve_mode(mode)
    return {
        "type": "mode",
        "mode": spec.id,
        "label": spec.label,
        "en": spec.en,
        "hint": spec.hint,
        "hr": spec.hr,
        "gets": list(spec.gets),
        "needs": list(spec.needs),
        "skips": list(spec.skips),
        "flags": {
            "raw": spec.raw,
            "spo2": spec.spo2,
            "hr": spec.hr,
            "poll": spec.poll,
        },
        "sections": list(spec.sections),
        "modes": [_mode_card(item) for item in MODES.values()],
    }
