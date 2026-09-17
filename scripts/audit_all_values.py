"""Audit every value the library can read against the real ring."""

from __future__ import annotations

import asyncio
import sys
import time
from collections import defaultdict

from gadgetpanda import Ring
from gadgetpanda.models import brand_display

ADDRESS = "EA1D0BD7-5438-F5F9-E624-9E8E750CCD38"


def _brief(value) -> str:
    text = brand_display(str(value))
    return text if len(text) <= 160 else text[:157] + "..."


async def _wait(items: list, timeout: float = 6.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if items:
            return True
        await asyncio.sleep(0.05)
    return False


async def main() -> int:
    ring = Ring(ADDRESS, name="RING503PANDA")
    events: dict[str, list] = defaultdict(list)
    gyro_nonzero = []

    def on_star(event: str, *args, **_kwargs) -> None:
        payload = args[0] if args else None
        events[event].append(payload)
        if event == "imu" and payload:
            if any(sample.gyro_mag2 for sample in payload):
                gyro_nonzero.append(payload)

    ring.on("*", on_star)
    rows: list[tuple[str, str, str]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        rows.append((name, "YES" if ok else "NO", detail))
        print(f"[{'YES' if ok else 'NO '}] {name:22} {_brief(detail)}")

    print(f"connecting {ADDRESS} …")
    try:
        await ring.connect(timeout=25)
    except Exception as exc:
        record("connect", False, str(exc))
        return 1

    try:
        record("connect", ring.connected, f"{ring.name} battery={ring.battery}")
        info = ring.info
        record("info.system_id", "system_id" in info, info.get("system_id", ""))
        record("info.model", "model" in info, info.get("model", ""))
        record("info.firmware", "firmware" in info, info.get("firmware", ""))
        record("info.hardware", "hardware" in info, info.get("hardware", ""))
        record("info.software", "software" in info, info.get("software", ""))
        record("info.vendor", info.get("vendor") == "gadgetpanda", info.get("vendor", ""))
        record("battery", ring.battery is not None, str(ring.battery))

        oneshots = [
            ("sport", ring.get_sport, "sport"),
            ("health", ring.get_health, "health"),
            ("temperature", ring.get_temperature, "temperature"),
            ("user", ring.get_user, "user_info"),
            ("birthday", ring.get_birthday, "birthday"),
            ("sport_history", ring.get_sport_history, "sport_history"),
            ("sleep_history", ring.get_sleep_history, "sleep_history_chunk"),
            ("raw_status", ring.get_raw_enabled, "raw_status"),
        ]
        for label, call, event in oneshots:
            events[event].clear()
            try:
                await call()
                ok = await _wait(events[event], 7)
                if label == "sleep_history" and not ok and events["sleep_history_complete"]:
                    ok = True
                record(label, ok, events[event][-1] if events[event] else "timeout")
            except Exception as exc:
                record(label, False, str(exc))
            await asyncio.sleep(0.25)

        begin = int((time.time() - 7 * 24 * 3600) * 1000)
        histories = [
            ("health_history", ring.get_health_history, "health_history", "health_history_complete"),
            ("hr_history", ring.get_heart_rate_history, "heart_rate_history", "heart_rate_history_complete"),
            ("ppg_history", ring.get_ppg_history, "ppg_history", "ppg_history_complete"),
        ]
        for label, call, event, done in histories:
            events[event].clear()
            events[done].clear()
            try:
                await call(begin)
                ok = await _wait(events[event], 8) or await _wait(events[done], 3)
                detail = events[event][-1] if events[event] else ("complete" if events[done] else "timeout")
                record(label, ok, detail)
            except Exception as exc:
                record(label, False, str(exc))
            await asyncio.sleep(0.25)

        events["spo2"].clear()
        try:
            await ring.set_spo2(True)
            ok = await _wait(events["spo2"], 8)
            record("spo2", ok, events["spo2"][-1] if events["spo2"] else "timeout")
        except Exception as exc:
            record("spo2", False, str(exc))

        events["heart_rate"].clear()
        events["hrv"].clear()
        events["imu"].clear()
        events["ppg"].clear()
        events["raw"].clear()
        await ring.start_realtime(interval=1.5)
        await asyncio.sleep(10)
        record("heart_rate", bool(events["heart_rate"] or ring.heart_rate), ring.heart_rate or "timeout")
        record("hrv", bool(events["hrv"] or ring.hrv), ring.hrv or "need RR x30")
        record("imu_acc", bool(ring.imu), ring.imu[0] if ring.imu else "timeout")
        record("imu_gyro", bool(gyro_nonzero), "nonzero" if gyro_nonzero else "all zero on wire")
        record("ppg", bool(ring.ppg), f"n={len(ring.ppg)}" if ring.ppg else "timeout")
        record("utc_ack", bool(events["utc"]), events["utc"][-1] if events["utc"] else "")
        record("sport_mode", bool(events["sport_mode"]), events["sport_mode"][-1] if events["sport_mode"] else "")

        skip = {
            "connect",
            "info.system_id",
            "info.model",
            "info.firmware",
            "info.hardware",
            "info.software",
            "info.vendor",
        }
        yes = [name for name, status, _ in rows if status == "YES" and name not in skip]
        no = [name for name, status, _ in rows if status == "NO" and name not in skip]
        print()
        print(f"lib+ring live: {len(yes)} yes / {len(no)} no")
        if no:
            print("missing:", ", ".join(no))
        return 0 if not no else 1
    finally:
        try:
            await ring.stop_realtime()
        except Exception:
            pass
        await ring.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
