"""Stream 6-axis IMU + PPG and print simple tap events."""

import asyncio

from gadgetpanda import Ring
from gadgetpanda.gesture import MotionWatch


async def main() -> None:
    watch = MotionWatch()
    ring = await Ring.find()

    def on_raw(frame) -> None:
        taps = watch.feed(frame.imu)
        if taps:
            print("gesture", taps)
        if frame.imu:
            sample = frame.imu[0]
            print(
                f"acc=({sample.acc_x:6d},{sample.acc_y:6d},{sample.acc_z:6d}) "
                f"gyro=({sample.gyro_x:6d},{sample.gyro_y:6d},{sample.gyro_z:6d}) "
                f"ppg={len(frame.ppg)}"
            )

    ring.on("raw", on_raw)

    async with ring:
        await ring.set_raw_enabled(True)
        print("raw stream on — move the ring, Ctrl+C to stop")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
