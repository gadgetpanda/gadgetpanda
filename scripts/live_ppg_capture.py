"""Capture a few seconds of realtime PPG from the known ring."""

from __future__ import annotations

import asyncio
import sys

from gadgetpanda import Ring

ADDRESS = "EA1D0BD7-5438-F5F9-E624-9E8E750CCD38"


async def main() -> int:
    ring = Ring(ADDRESS, name="RING503PANDA")
    frames = []
    ring.on("ppg", frames.append)
    ring.on("heart_rate", lambda sample: print("hr", sample.bpm, "bpm"))
    print(f"connecting {ADDRESS} …")
    await ring.connect(timeout=25)
    try:
        print(f"connected {ring.name} battery={ring.battery}")
        await ring.start_ppg()
        deadline = asyncio.get_running_loop().time() + 8
        while asyncio.get_running_loop().time() < deadline and len(frames) < 8:
            await asyncio.sleep(0.05)
        print(f"ppg_frames={len(frames)}")
        for samples in frames[:6]:
            values = " ".join(str(sample.value) for sample in samples)
            print(f"ppg flag={samples[0].flag} n={len(samples)} {values}")
        ok = bool(frames)
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        try:
            await ring.set_raw_enabled(False)
        except Exception:
            pass
        await ring.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
