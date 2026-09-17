"""Live BLE tests. Requires a nearby RING503PANDA ring.

    PANDA_E2E=1 pytest -m hardware
"""

from __future__ import annotations

import os

import pytest

from gadgetpanda import Ring
from gadgetpanda.ring import wait_until

pytestmark = [pytest.mark.hardware, pytest.mark.e2e]

skip_live = pytest.mark.skipif(
    os.environ.get("PANDA_E2E") != "1",
    reason="set PANDA_E2E=1 and keep a RING503PANDA ring nearby",
)


@skip_live
@pytest.mark.asyncio
async def test_live_scan_connect_and_heart_rate():
    devices = await Ring.scan(timeout=8)
    assert devices, "ไม่พบแหวนตอนสแกนจริง"

    ring = Ring(devices[0])
    heart = []
    sport = []
    ring.on("heart_rate", heart.append)
    ring.on("sport", sport.append)

    async with ring:
        assert ring.connected
        await ring.get_sport()
        try:
            await wait_until(lambda: bool(heart or sport or ring.battery is not None), timeout=12)
        except TimeoutError:
            pytest.fail("ต่อแหวนได้แต่ไม่ได้รับ heart rate / sport / battery")

    assert ring.info or ring.battery is not None or heart or sport
