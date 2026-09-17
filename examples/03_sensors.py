"""Stream every live sensor: sport, health, temperature, SpO2, HR, IMU, PPG."""

import asyncio

from gadgetpanda import Ring


async def main() -> None:
    ring = await Ring.find()
    ring.on("sport", print)
    ring.on("health", print)
    ring.on("temperature", print)
    ring.on("spo2", print)
    ring.on("heart_rate", lambda sample: print("hr", sample.bpm, "rr", sample.rr_intervals))
    ring.on("hrv", lambda hrv: print("hrv", round(hrv.sdnn_ms, 2), "ms"))
    ring.on("imu", lambda samples: print("imu", samples[0] if samples else None))
    ring.on("ppg", lambda samples: print("ppg", [item.value for item in samples]))

    async with ring:
        await ring.start_realtime()
        print("realtime on — Ctrl+C to stop")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
