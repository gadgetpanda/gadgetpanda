"""Confirm every live sensor arrives from the known ring."""

from __future__ import annotations

import asyncio
import sys

from gadgetpanda import Ring

ADDRESS = "EA1D0BD7-5438-F5F9-E624-9E8E750CCD38"


async def main() -> int:
    ring = Ring(ADDRESS, name="RING503PANDA")
    ring.on("raw_status", lambda enabled: print("raw_status", enabled))
    ring.on("spo2", lambda spo2: print("spo2", spo2))
    ring.on("error", lambda exc, packet=None: print("error", exc))
    print(f"connecting {ADDRESS} …")
    await ring.connect(timeout=25)
    try:
        print(f"connected {ring.name} battery={ring.battery}")
        await ring.start_realtime(interval=1.5)
        await asyncio.sleep(10)
        snap = ring.snapshot()
        checks = {
            "battery": snap["battery"] is not None,
            "heart_rate": snap["heart_rate"] is not None,
            "sport": snap["sport"] is not None,
            "health": snap["health"] is not None,
            "temperature": snap["temperature"] is not None,
            "spo2": snap["spo2"] is not None,
            "imu": bool(snap["imu"]),
            "ppg": bool(snap["ppg"]),
        }
        for name, ok in checks.items():
            value = snap[name]
            print(f"[{'PASS' if ok else 'FAIL'}] {name}  {value}")
        return 0 if all(checks.values()) else 1
    finally:
        await ring.stop_realtime()
        await ring.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
