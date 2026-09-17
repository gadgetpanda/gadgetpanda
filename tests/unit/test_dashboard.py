from __future__ import annotations

import unittest

from gadgetpanda.dashboard.server import Hub, _profile_int
from gadgetpanda.stream import mode_payload


class TestProfileInt(unittest.TestCase):
    def test_accepts_in_range(self):
        self.assertEqual(_profile_int("28", 1, 120, "อายุ"), 28)
        self.assertEqual(_profile_int(170, 80, 250, "ส่วนสูง"), 170)

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError) as cm:
            _profile_int(300, 80, 250, "ส่วนสูง")
        self.assertIn("ส่วนสูง", str(cm.exception))

    def test_rejects_non_int(self):
        with self.assertRaises(ValueError):
            _profile_int("abc", 1, 120, "อายุ")


class TestHubMode(unittest.IsolatedAsyncioTestCase):
    async def test_set_mode_without_ring(self):
        hub = Hub(mode="all")
        await hub.set_mode("ppg")
        self.assertEqual(hub.mode, "ppg")
        self.assertEqual(hub.latest["mode"]["mode"], "ppg")

    async def test_set_user_without_ring(self):
        hub = Hub()
        await hub.set_user({"age": 30, "weight_kg": 70, "height_cm": 170})
        self.assertEqual(hub.latest["user_status"]["ok"], False)
        self.assertIn("ยังไม่ต่อ", hub.latest["user_status"]["error"])

    async def test_set_user_validation(self):
        hub = Hub()

        class FakeRing:
            connected = True

            async def set_user(self, *args, **kwargs):
                raise AssertionError("should not set invalid profile")

            async def get_user(self):
                return None

        hub.ring = FakeRing()
        await hub.set_user({"age": 999, "weight_kg": 70, "height_cm": 170})
        self.assertFalse(hub.latest["user_status"]["ok"])
        self.assertIn("อายุ", hub.latest["user_status"]["error"])

    async def test_welcome_includes_mode(self):
        hub = Hub(mode="motion")
        sent = []

        class FakeSocket:
            async def send_text(self, text: str):
                sent.append(text)

        await hub.welcome(FakeSocket())
        self.assertTrue(any('"type": "mode"' in item or '"type":"mode"' in item for item in sent))
        self.assertTrue(any("motion" in item for item in sent))
        self.assertEqual(mode_payload("motion")["mode"], "motion")


if __name__ == "__main__":
    unittest.main()
