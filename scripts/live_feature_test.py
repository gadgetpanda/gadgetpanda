"""Live feature sweep against one RING503PANDA.

Does not call restore() or enter_dfu().
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import defaultdict

from gadgetpanda import Ring
from gadgetpanda.models import brand_display

ADDRESS = "EA1D0BD7-5438-F5F9-E624-9E8E750CCD38"
NAME = "RING503PANDA-0000090"


def _brief(value) -> str:
    text = brand_display(str(value))
    if len(text) > 240:
        return text[:237] + "..."
    return text


async def _wait(got: list, timeout: float = 6.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if got:
            return True
        await asyncio.sleep(0.05)
    return False


async def main() -> int:
    ring = Ring(ADDRESS, name=NAME)
    events: dict[str, list] = defaultdict(list)
    errors: list[str] = []
    raw_cmds: list[str] = []

    def on_star(event: str, *args, **kwargs) -> None:
        if event == "error":
            errors.append(_brief(args[0] if args else kwargs))
            if len(args) > 1 and isinstance(args[1], (bytes, bytearray)):
                raw_cmds.append(bytes(args[1]).hex())
            return
        if event == "raw_command":
            packet = args[0] if args else b""
            raw_cmds.append(getattr(packet, "hex", lambda: str(packet))())
        payload = args[0] if args else kwargs
        events[event].append(payload)

    ring.on("*", on_star)

    results: list[tuple[str, str, str]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, "PASS" if ok else "FAIL", detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}")

    print(f"connecting {ADDRESS} as {NAME} …")
    try:
        await ring.connect(timeout=25)
    except Exception as exc:
        record("connect", False, _brief(exc))
        for name, status, detail in results:
            print(f"{status:4}  {name}: {detail}")
        return 1

    try:
        record(
            "connect",
            ring.connected,
            f"name={ring.name} battery={ring.battery} info={json.dumps(ring.info, ensure_ascii=False)}",
        )
        record("display_name", ring.name == NAME or ring.name.startswith("RING503PANDA"), ring.name)
        record("brand_vendor", ring.info.get("vendor") == "gadgetpanda", str(ring.info.get("vendor")))
        dumped = json.dumps(ring.info)
        from gadgetpanda.models import oem_vendor_mark

        record(
            "brand_model",
            oem_vendor_mark().lower() not in dumped.lower() and "RL503" not in dumped,
            str(ring.info),
        )
        record("battery", ring.battery is not None, str(ring.battery))

        checks = [
            ("sport", ring.get_sport, "sport"),
            ("health", ring.get_health, "health"),
            ("temperature", ring.get_temperature, "temperature"),
            ("user", ring.get_user, "user_info"),
            ("birthday", ring.get_birthday, "birthday"),
            ("sport_history", ring.get_sport_history, "sport_history"),
            ("sleep_history", ring.get_sleep_history, "sleep_history_chunk"),
            ("raw_status", ring.get_raw_enabled, "raw_status"),
        ]

        for label, call, event in checks:
            events[event].clear()
            try:
                await call()
                ok = await _wait(events[event], 8)
                extra = ""
                if event == "sleep_history_chunk" and not ok and events["sleep_history_complete"]:
                    ok = True
                    extra = "complete-only"
                record(label, ok, extra or _brief(events[event][-1] if events[event] else "timeout"))
            except Exception as exc:
                record(label, False, _brief(exc))
            await asyncio.sleep(0.3)

        begin = int((time.time() - 7 * 24 * 3600) * 1000)
        for label, call, event, done in (
            ("health_history", ring.get_health_history, "health_history", "health_history_complete"),
            ("heart_rate_history", ring.get_heart_rate_history, "heart_rate_history", "heart_rate_history_complete"),
        ):
            events[event].clear()
            events[done].clear()
            try:
                await call(begin)
                ok = await _wait(events[event], 10) or await _wait(events[done], 4)
                detail = events[event][-1] if events[event] else ("complete" if events[done] else "timeout")
                record(label, ok, _brief(detail))
            except Exception as exc:
                record(label, False, _brief(exc))
            await asyncio.sleep(0.4)

        ppg_ok = False
        ppg_detail = "timeout"
        events["ppg_history"].clear()
        events["ppg_history_complete"].clear()
        for begin_ms in (begin, 0):
            try:
                await ring.get_ppg_history(begin_ms)
            except Exception as exc:
                ppg_detail = _brief(exc)
                continue
            if await _wait(events["ppg_history"], 6) or await _wait(events["ppg_history_complete"], 3):
                ppg_ok = True
                ppg_detail = events["ppg_history"][-1] if events["ppg_history"] else "complete"
                break
            await asyncio.sleep(0.5)
        record("ppg_history", ppg_ok, _brief(ppg_detail))

        events["raw"].clear()
        events["raw_status"].clear()
        events["heart_rate"].clear()
        events["spo2"].clear()
        try:
            await ring.set_raw_enabled(True)
            ok_raw = await _wait(events["raw"], 8)
            frame = events["raw"][-1] if events["raw"] else None
            raw_detail = (
                f"imu={len(frame.imu)} ppg={len(frame.ppg)} status={events['raw_status'][-1] if events['raw_status'] else None}"
                if frame is not None
                else "timeout"
            )
            record("raw_imu_ppg", ok_raw, raw_detail)

            await ring.set_spo2(True)
            ok_spo2 = await _wait(events["spo2"], 10)
            record("spo2", ok_spo2, _brief(events["spo2"][-1] if events["spo2"] else "timeout"))

            ok_hr = await _wait(events["heart_rate"], 18)
            wrist = next((text for text in events["debug"] if "onwrist" in str(text).lower()), "")
            hr_detail = events["heart_rate"][-1] if events["heart_rate"] else (wrist or "timeout — สวมแหวนให้แน่นแล้วลองใหม่")
            record("heart_rate", ok_hr, _brief(hr_detail))
        except Exception as exc:
            record("raw_imu_ppg", False, _brief(exc))
            record("spo2", False, _brief(exc))
            record("heart_rate", False, _brief(exc))
        finally:
            try:
                await ring.set_raw_enabled(False)
            except Exception:
                pass

        try:
            await ring.set_sport_mode(True)
            await asyncio.sleep(0.4)
            await ring.set_sport_mode(False)
            record("sport_mode", True, "on then off")
        except Exception as exc:
            record("sport_mode", False, _brief(exc))

        try:
            await ring.set_utc()
            record("set_utc", True, "sent")
        except Exception as exc:
            record("set_utc", False, _brief(exc))

        if events["user_info"]:
            user = events["user_info"][-1]
            try:
                await ring.set_user(user.age, user.sex, user.weight_kg, user.height_cm, user.user_id)
                record("set_user", True, "wrote same profile back")
            except Exception as exc:
                record("set_user", False, _brief(exc))
        else:
            record("set_user", False, "skipped — no user_info")

        if events["birthday"]:
            bday = events["birthday"][-1]
            try:
                await ring.set_birthday(bday.year, bday.month, bday.day)
                record("set_birthday", True, "wrote same birthday back")
            except Exception as exc:
                record("set_birthday", False, _brief(exc))
        else:
            record("set_birthday", False, "skipped — no birthday")

        record("rx_errors", not errors, _brief(errors) if errors else "none")
        if raw_cmds:
            print("unknown_rx", raw_cmds[:8])

    finally:
        await ring.disconnect()
        record("disconnect", True, "done")

    print()
    failed = [name for name, status, _ in results if status == "FAIL"]
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("failed:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
