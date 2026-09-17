"""Scan for RING503PANDA / RING503nPANDA rings."""

import asyncio

from gadgetpanda import Ring


async def main() -> None:
    print("scanning 8s …")
    devices = await Ring.scan(timeout=8)
    if not devices:
        print("ไม่พบแหวน — เปิด Bluetooth แล้วให้แหวนอยู่ใกล้เครื่อง")
        return
    for device in devices:
        rssi = f"{device.rssi} dBm" if device.rssi is not None else "?"
        print(f"{device.address}  {rssi:>10}  {device.display_name}")


if __name__ == "__main__":
    asyncio.run(main())
