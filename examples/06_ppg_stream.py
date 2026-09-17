"""Stream realtime PPG samples from the optical sensor."""

import asyncio

from gadgetpanda import Ring


async def main() -> None:
    ring = await Ring.find()

    def on_ppg(samples) -> None:
        if not samples:
            return
        values = " ".join(str(sample.value) for sample in samples)
        print(f"ppg flag={samples[0].flag} n={len(samples)} {values}")

    ring.on("ppg", on_ppg)
    ring.on("heart_rate", lambda sample: print("hr", sample.bpm, "bpm"))

    async with ring:
        await ring.start_ppg()
        print("ppg streaming — wear the ring, Ctrl+C to stop")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
