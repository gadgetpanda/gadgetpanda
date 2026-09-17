"""Connect and print device info + battery + heart rate."""

import asyncio

from gadgetpanda import Ring


async def main() -> None:
    ring = await Ring.find()
    ring.on("heart_rate", lambda sample: print(f"HR {sample.bpm} bpm  rr={sample.rr_intervals}"))
    ring.on("battery", lambda level: print(f"battery {level}%"))

    async with ring:
        print("connected", ring.name, ring.address)
        print("info", ring.info)
        print("listening 20s …")
        await asyncio.sleep(20)


if __name__ == "__main__":
    asyncio.run(main())
