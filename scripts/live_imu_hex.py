"""Dump one 0x99 IMU frame as hex to see gyro bytes."""

from __future__ import annotations

import asyncio
import sys

from gadgetpanda import Ring
from gadgetpanda.protocol import i16be, parse_rx, u8

ADDRESS = "EA1D0BD7-5438-F5F9-E624-9E8E750CCD38"


def i16le(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little", signed=True)


async def main() -> int:
    ring = Ring(ADDRESS, name="RING503PANDA")
    packets: list[bytes] = []

    orig = ring._on_rx

    def tap(_char, data) -> None:
        raw = bytes(data)
        if raw[2:3] == b"\x99":
            packets.append(raw)
        orig(_char, data)

    ring._on_rx = tap
    await ring.connect(timeout=25)
    try:
        await ring.start_ppg()
        deadline = asyncio.get_running_loop().time() + 6
        while asyncio.get_running_loop().time() < deadline and len(packets) < 3:
            await asyncio.sleep(0.05)
        if not packets:
            print("FAIL no 0x99")
            return 1
        for packet in packets[:2]:
            n6d = u8(packet, 8)
            imu = packet[9 : 9 + n6d]
            print(f"len={len(packet)} n6d={n6d} imu_hex={imu.hex()}")
            for off in range(0, len(imu) // 12 * 12, 12):
                chunk = imu[off : off + 12]
                print(
                    "  be",
                    [i16be(chunk, 0), i16be(chunk, 2), i16be(chunk, 4), i16be(chunk, 6), i16be(chunk, 8), i16be(chunk, 10)],
                    "le",
                    [i16le(chunk, 0), i16le(chunk, 2), i16le(chunk, 4), i16le(chunk, 6), i16le(chunk, 8), i16le(chunk, 10)],
                    "raw",
                    chunk.hex(),
                )
            parsed = parse_rx(packet)
            if parsed:
                print("  parsed", parsed[0].payload.imu[:2])
        return 0
    finally:
        await ring.set_raw_enabled(False)
        await ring.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
