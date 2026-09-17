#!/usr/bin/env python3
"""Scan for fun-dog BLE advertisements."""

from __future__ import annotations

import asyncio

from gadgetpanda.dog import Dog


async def main() -> None:
    devices = await Dog.scan(timeout=8.0, loose=True)
    if not devices:
        print("ไม่พบอุปกรณ์ — ลองเปิดสุนัขและ BLE")
        return
    for device in devices:
        print(f"{device.address}  {device.rssi or '':>4}  {device.display_name}")


if __name__ == "__main__":
    asyncio.run(main())
