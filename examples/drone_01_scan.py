"""Probe default drone gateway IPs after joining the craft Wi‑Fi."""

import asyncio

from gadgetpanda.drone import Drone


async def main() -> None:
    devices = await Drone.scan(timeout=1.5, model="v66")
    for device in devices:
        print(device.display_name)
    if devices:
        print("next: gadgetpanda drone connect", devices[0].host)


if __name__ == "__main__":
    asyncio.run(main())
