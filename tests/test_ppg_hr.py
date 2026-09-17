import math

from gadgetpanda.models import PpgHrTracker, _ppg_channel


def test_ppg_channel_splits_interleaved_bands():
    ir = [14_220_000 + i * 10 for i in range(8)]
    red = [12_880_000 + i * 80 for i in range(8)]
    interleaved = [item for pair in zip(ir, red) for item in pair]
    channel = _ppg_channel(interleaved)
    assert channel == red


def test_ppg_hr_estimates_72bpm_from_sine():
    tracker = PpgHrTracker()
    hz = 50
    bpm = 72
    found = None
    for packet in range(1, 40):
        now = packet * 0.2
        samples = []
        for index in range(10):
            t = now - 0.2 + (index + 1) * (0.2 / 10)
            ir = 1_200_000 + int(80_000 * math.sin(2 * math.pi * (bpm / 60) * t))
            red = 900_000
            samples.extend((ir, red))
        found = tracker.feed(samples, now) or found
    assert found is not None
    assert found.source == "ppg"
    assert abs(found.bpm - 72) <= 8
