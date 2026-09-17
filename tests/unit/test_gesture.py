from __future__ import annotations

import unittest

from gadgetpanda.gesture import MotionWatch
from gadgetpanda.models import Raw6D


class TestMotionWatch(unittest.TestCase):
    def test_magnitude(self):
        watch = MotionWatch()
        self.assertAlmostEqual(watch.magnitude(Raw6D(3, 4, 0, 0, 0, 0)), 5.0)

    def test_detects_tap(self):
        watch = MotionWatch(tap_threshold=1000)
        baseline = (Raw6D(0, 0, 1000, 0, 0, 0),)
        spike = (Raw6D(0, 0, 20000, 0, 0, 0),)
        self.assertEqual(watch.feed(baseline), [])
        self.assertEqual(watch.feed(spike), ["tap"])

    def test_no_tap_when_quiet(self):
        watch = MotionWatch(tap_threshold=18000)
        samples = tuple(Raw6D(i, 0, 1000, 0, 0, 0) for i in range(5))
        self.assertEqual(watch.feed(samples), [])


if __name__ == "__main__":
    unittest.main()
