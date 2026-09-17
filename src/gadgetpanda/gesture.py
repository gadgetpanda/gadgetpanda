"""Simple IMU helpers for maker experiments.

This is not a trained classifier. It turns 6-axis samples into
easy motion features so a senior project can start in one file.
"""

from __future__ import annotations

import math
from collections import deque

from gadgetpanda.models import Raw6D


class MotionWatch:
    def __init__(self, tap_threshold: float = 18000, window: int = 12):
        self.tap_threshold = tap_threshold
        self._mags: deque[float] = deque(maxlen=window)
        self._last_tap = 0.0

    def magnitude(self, sample: Raw6D) -> float:
        return math.sqrt(sample.acc_x**2 + sample.acc_y**2 + sample.acc_z**2)

    def feed(self, samples: tuple[Raw6D, ...]) -> list[str]:
        events: list[str] = []
        for sample in samples:
            mag = self.magnitude(sample)
            prev = self._mags[-1] if self._mags else mag
            self._mags.append(mag)
            if mag - prev > self.tap_threshold:
                events.append("tap")
        return events
