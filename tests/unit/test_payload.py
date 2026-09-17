from __future__ import annotations

import unittest
from types import SimpleNamespace

from gadgetpanda.dashboard.payload import encode_event, encode_snapshot
from gadgetpanda.models import BloodOxygen, Health, HeartRate, Hrv, PpgSample, Raw6D, Sport, Temperature, UserInfo, oem_vendor_mark


class TestEncodeEvent(unittest.TestCase):
    def test_battery_and_info(self):
        self.assertEqual(encode_event("battery", 44)["value"], 44)
        info = encode_event("info", {"vendor": oem_vendor_mark(), "model": "RL503"})
        self.assertEqual(info["info"]["vendor"], "gadgetpanda")
        self.assertEqual(info["info"]["model"], "RING503PANDA")

    def test_heart_rate_and_hrv(self):
        heart = encode_event("heart_rate", HeartRate(bpm=72, rr_intervals=(800, 820)))
        self.assertEqual(heart, {"type": "heart_rate", "bpm": 72, "rr": [800, 820], "source": "ble"})
        estimated = encode_event("heart_rate", HeartRate(bpm=68, source="ppg"))
        self.assertEqual(estimated["source"], "ppg")
        hrv = encode_event("hrv", Hrv(sdnn=12.5, sdnn_ms=12.2, samples=29))
        self.assertEqual(hrv["sdnn_ms"], 12.2)

    def test_grouped_sensors(self):
        sport = encode_event("sport", Sport(steps=1840, distance_m=125.0, calories_kcal=3.7))
        self.assertEqual(sport["steps"], 1840)
        health = encode_event("health", Health(42, 16, 3, 4, 80))
        self.assertEqual(health["stamina"], 80)
        temp = encode_event("temperature", Temperature(26.5, 31.2, 36.6))
        self.assertEqual(temp["body_c"], 36.6)
        spo2 = encode_event("spo2", BloodOxygen(True, 98, True))
        self.assertTrue(spo2["on_wrist"])

    def test_imu_peak_gyro_and_ppg(self):
        imu = encode_event(
            "imu",
            (Raw6D(10, 20, 30, 0, 0, 0), Raw6D(11, 21, 31, 3, 4, 12)),
        )
        self.assertEqual(imu["acc"], [10, 20, 30])
        self.assertEqual(imu["gyro"], [3, 4, 12])
        ppg = encode_event("ppg", (PpgSample(1, 1200), PpgSample(1, 1210)))
        self.assertEqual(ppg["values"], [1200, 1210])

    def test_user_connected_disconnected(self):
        user = encode_event("user_info", UserInfo(32, 0, 58, 162, 81))
        self.assertEqual(user["age"], 32)
        self.assertEqual(user["user_id"], 81)
        connected = encode_event("connected", SimpleNamespace(name="RING", address="AA", battery=50))
        self.assertEqual(connected["name"], "RING")
        self.assertEqual(encode_event("disconnected", None)["type"], "disconnected")

    def test_unknown_and_empty(self):
        self.assertIsNone(encode_event("unknown", 1))
        self.assertIsNone(encode_event("imu", ()))
        self.assertIsNone(encode_event("ppg", ()))


class TestEncodeSnapshot(unittest.TestCase):
    def test_skips_empty(self):
        ring = SimpleNamespace(
            info={"vendor": "gadgetpanda"},
            battery=44,
            heart_rate=HeartRate(bpm=68),
            hrv=None,
            sport=None,
            health=None,
            temperature=None,
            spo2=None,
            user=None,
            imu=None,
            ppg=None,
        )
        types = [item["type"] for item in encode_snapshot(ring)]
        self.assertEqual(types, ["info", "battery", "heart_rate"])

    def test_includes_user(self):
        ring = SimpleNamespace(
            info={},
            battery=None,
            heart_rate=None,
            hrv=None,
            sport=None,
            health=None,
            temperature=None,
            spo2=None,
            user=UserInfo(28, 1, 70, 175, 81),
            imu=None,
            ppg=None,
        )
        messages = encode_snapshot(ring)
        self.assertEqual(messages[0]["type"], "user")
        self.assertEqual(messages[0]["weight_kg"], 70)


if __name__ == "__main__":
    unittest.main()
