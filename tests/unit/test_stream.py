from __future__ import annotations

import unittest

from gadgetpanda.stream import DEFAULT_MODE, MODES, allows_event, mode_payload, resolve_mode


class TestStreamModes(unittest.TestCase):
    def test_all_modes_registered(self):
        self.assertEqual(set(MODES), {"all", "hr", "ppg", "vitals", "motion", "activity"})
        self.assertEqual(DEFAULT_MODE, "all")

    def test_resolve_unknown_falls_back(self):
        self.assertEqual(resolve_mode(None).id, "all")
        self.assertEqual(resolve_mode("nope").id, "all")
        self.assertEqual(resolve_mode("ppg").hr, "ppg")
        self.assertFalse(resolve_mode("hr").raw)

    def test_allows_core_always(self):
        for mode in MODES:
            self.assertTrue(allows_event(mode, "battery"))
            self.assertTrue(allows_event(mode, "user_status"))
            self.assertTrue(allows_event(mode, "mode"))

    def test_allows_filters_by_mode(self):
        self.assertTrue(allows_event("hr", "heart_rate"))
        self.assertFalse(allows_event("hr", "ppg"))
        self.assertTrue(allows_event("all", "imu"))
        self.assertTrue(allows_event("ppg", "ppg"))
        self.assertFalse(allows_event("ppg", "sport"))
        self.assertTrue(allows_event("motion", "imu"))
        self.assertFalse(allows_event("motion", "heart_rate"))

    def test_mode_payload_shape(self):
        payload = mode_payload("vitals")
        self.assertEqual(payload["type"], "mode")
        self.assertEqual(payload["mode"], "vitals")
        self.assertEqual(payload["hr"], "ble")
        self.assertTrue(payload["gets"])
        self.assertTrue(payload["needs"])
        self.assertIn("temperature", payload["sections"])
        self.assertEqual([item["id"] for item in payload["modes"]], list(MODES))
        self.assertIn("gets", payload["modes"][0])


if __name__ == "__main__":
    unittest.main()
