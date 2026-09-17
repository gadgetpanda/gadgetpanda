from __future__ import annotations

import unittest

from gadgetpanda.ring import Ring, wait_until
from gadgetpanda.testing import FakeBleClient, SimulatedRing


class TestRingUnit(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.firmware = SimulatedRing()
        self.ring = Ring(self.firmware.advertised(), transport=FakeBleClient(self.firmware))

    async def test_connect_reads_branded_profile(self):
        await self.ring.connect()
        try:
            self.assertTrue(self.ring.connected)
            self.assertEqual(self.ring.info["vendor"], "gadgetpanda")
            self.assertEqual(self.ring.info["model"], "RING503PANDA")
            self.assertEqual(self.ring.battery, 87)
        finally:
            await self.ring.disconnect()
            self.assertFalse(self.ring.connected)

    async def test_start_realtime_fills_live_values(self):
        async with self.ring:
            self.firmware.push_heart_rate(72)
            await self.ring.start_realtime(interval=0.2)
            await wait_until(
                lambda: all(
                    (
                        self.ring.sport,
                        self.ring.health,
                        self.ring.temperature,
                        self.ring.ppg,
                        self.ring.imu,
                        self.ring.heart_rate,
                        self.ring.battery is not None,
                    )
                )
            )
            self.assertTrue(self.firmware.raw_enabled)
            snap = self.ring.snapshot()
            await self.ring.stop_realtime()
        self.assertEqual(snap["sport"].steps, 1840)
        self.assertEqual(snap["ppg"][0].value, 1200)
        self.assertEqual(snap["heart_rate"].bpm, 72)

    async def test_vitals_mode_enables_spo2_not_raw(self):
        async with self.ring:
            await self.ring.apply_stream("vitals", interval=0.2)
            await wait_until(lambda: self.ring.spo2 is not None)
            self.assertFalse(self.firmware.raw_enabled)
            self.assertEqual(self.ring.spo2.spo2, 98)

    async def test_apply_stream_switches_modes(self):
        async with self.ring:
            await self.ring.apply_stream("hr", interval=0.2)
            self.assertEqual(self.ring.stream_mode, "hr")
            self.assertEqual(self.ring.hr_source, "ble")
            self.firmware.push_heart_rate(77)
            await wait_until(lambda: self.ring.heart_rate and self.ring.heart_rate.bpm == 77)
            await self.ring.apply_stream("ppg", interval=0.2)
            self.assertEqual(self.ring.hr_source, "ppg")
            await self.ring.apply_stream("motion", interval=0.2)
            self.assertEqual(self.ring.stream_mode, "motion")
            self.assertEqual(self.ring.hr_source, "off")

    async def test_set_user_keeps_existing_sex_and_id(self):
        async with self.ring:
            await self.ring.get_user()
            await wait_until(lambda: self.ring.user is not None)
            await self.ring.set_user(32, None, 78, 182)
            await wait_until(lambda: self.ring.user and self.ring.user.age == 32)
        self.assertEqual(self.firmware.user["age"], 32)
        self.assertEqual(self.firmware.user["weight_kg"], 78)
        self.assertEqual(self.firmware.user["height_cm"], 182)
        self.assertEqual(self.firmware.user["sex"], 1)
        self.assertEqual(self.firmware.user["user_id"], 81)

    async def test_start_ppg_enables_raw(self):
        async with self.ring:
            await self.ring.start_ppg()
            await wait_until(lambda: bool(self.ring.ppg))
            self.assertTrue(self.firmware.raw_enabled)
            self.assertEqual(self.ring.stream_mode, "ppg")

    async def test_hrv_from_rr_window(self):
        seen = []
        self.ring.on("hrv", seen.append)
        async with self.ring:
            for _ in range(30):
                self.firmware.push_heart_rate(72, rr=(800, 820))
            await wait_until(lambda: bool(seen))
        self.assertGreater(seen[-1].sdnn_ms, 0)

    async def test_scan_filters_with_discover(self):
        async def discover(_timeout: float):
            return [
                self.firmware.advertised(),
            ]

        found = await Ring.scan(discover=discover)
        self.assertEqual(found[0].address, self.firmware.address)


class TestWaitUntil(unittest.IsolatedAsyncioTestCase):
    async def test_timeout(self):
        with self.assertRaises(TimeoutError):
            await wait_until(lambda: False, timeout=0.05)


if __name__ == "__main__":
    unittest.main()
