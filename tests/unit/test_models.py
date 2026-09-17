from __future__ import annotations

import math
import unittest

from gadgetpanda.models import (
    AdvertisedRing,
    EventBus,
    HeartRate,
    HrvTracker,
    PpgHrTracker,
    Raw6D,
    brand_display,
    brand_display_value,
    calculate_hrv,
    oem_vendor_mark,
    panda_display_name,
    _ppg_channel,
)


class TestBranding(unittest.TestCase):
    def test_brand_display_replacements(self):
        oem = oem_vendor_mark()
        self.assertEqual(brand_display(f"{oem} RL503"), "gadgetpanda RING503PANDA")
        self.assertEqual(brand_display("RL503N-ABC"), "RING503nPANDA-ABC")

    def test_brand_display_value_nested(self):
        value = brand_display_value({"vendor": oem_vendor_mark(), "names": ["RL503", 1]})
        self.assertEqual(value["vendor"], "gadgetpanda")
        self.assertEqual(value["names"][0], "RING503PANDA")

    def test_panda_display_name(self):
        self.assertEqual(panda_display_name("RL503-0000090", "AA:BB"), "RING503PANDA-0000090")
        self.assertTrue(panda_display_name(None, "EA1D0BD7").startswith("EA1D") or "EA1D0BD7" in panda_display_name(None, "EA1D0BD7"))
        advertised = AdvertisedRing("RL503-E2E", "AA:BB:CC:DD:EE:10", -40)
        self.assertIn("RING503PANDA", advertised.display_name)


class TestHrv(unittest.TestCase):
    def test_calculate_hrv_filters_window(self):
        self.assertEqual(calculate_hrv([400, 800, 820]), calculate_hrv([800, 820]))
        self.assertEqual(calculate_hrv([800]), 0.0)

    def test_tracker_emits_after_thirty_packets(self):
        tracker = HrvTracker()
        last = None
        for _ in range(30):
            last = tracker.feed((800, 820))
        self.assertIsNotNone(last)
        self.assertGreater(last.sdnn_ms, 0)
        self.assertEqual(last.samples, 29)

    def test_tracker_clears_after_none_limit(self):
        tracker = HrvTracker()
        tracker.feed((800, 820))
        cleared = None
        for _ in range(HrvTracker.NONE_LIMIT + 1):
            cleared = tracker.feed(())
        self.assertIsNotNone(cleared)
        self.assertEqual(cleared.sdnn, 0.0)

    def test_tracker_reset(self):
        tracker = HrvTracker()
        tracker.feed((800, 820))
        tracker.reset()
        self.assertIsNone(tracker.feed((800, 820)))


class TestPpgHr(unittest.TestCase):
    def test_channel_picks_variable_band(self):
        ir = [14_220_000 + i * 10 for i in range(8)]
        red = [12_880_000 + i * 80 for i in range(8)]
        interleaved = [item for pair in zip(ir, red) for item in pair]
        self.assertEqual(_ppg_channel(interleaved), red)

    def test_estimates_near_72bpm(self):
        tracker = PpgHrTracker()
        bpm = 72
        found = None
        for packet in range(1, 40):
            now = packet * 0.2
            samples = []
            for index in range(10):
                t = now - 0.2 + (index + 1) * (0.2 / 10)
                ir = 1_200_000 + int(80_000 * math.sin(2 * math.pi * (bpm / 60) * t))
                samples.extend((ir, 900_000))
            found = tracker.feed(samples, now) or found
        self.assertIsNotNone(found)
        self.assertEqual(found.source, "ppg")
        self.assertLessEqual(abs(found.bpm - 72), 8)

    def test_reset_clears_state(self):
        tracker = PpgHrTracker()
        tracker.feed([1000, 1100, 1000, 1100], 1.0)
        tracker.reset()
        self.assertIsNone(tracker.feed([1000, 1100, 1000, 1100], 1.2))


class TestRaw6DAndBus(unittest.TestCase):
    def test_gyro_mag2(self):
        sample = Raw6D(1, 2, 3, 3, 4, 12)
        self.assertEqual(sample.gyro_mag2, 3 * 3 + 4 * 4 + 12 * 12)

    def test_event_bus_star_and_specific(self):
        bus = EventBus()
        seen = []
        star = []
        bus.on("heart_rate", seen.append)
        bus.on("*", lambda event, *args, **kwargs: star.append((event, args)))
        bus.emit("heart_rate", HeartRate(bpm=70))
        self.assertEqual(seen[0].bpm, 70)
        self.assertEqual(star[0][0], "heart_rate")


if __name__ == "__main__":
    unittest.main()
