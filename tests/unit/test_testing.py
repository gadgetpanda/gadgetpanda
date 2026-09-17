from __future__ import annotations

import unittest

from gadgetpanda.protocol import CMD_GET_USER, CMD_SET_USER, UUID_HR_MEASUREMENT, pack
from gadgetpanda.testing import FakeBleClient, SimulatedRing


class TestSimulatedRing(unittest.TestCase):
    def test_set_user_updates_and_echoes(self):
        firmware = SimulatedRing()
        seen = []
        firmware.attach({UUID_HR_MEASUREMENT: lambda *_a: None})
        firmware._notify = {
            "aae28f01-71b5-42a1-8c3c-f9cf6ac969d0": lambda _c, data: seen.append(bytes(data)),
        }
        firmware.write("aae28f02-71b5-42a1-8c3c-f9cf6ac969d0", pack(CMD_SET_USER, bytes([32, 0, 78, 182]) + (81).to_bytes(5, "big")))
        self.assertEqual(firmware.user["age"], 32)
        self.assertEqual(firmware.user["sex"], 0)
        self.assertTrue(seen)
        self.assertEqual(seen[0][2], CMD_GET_USER)

    def test_push_heart_rate_and_battery(self):
        firmware = SimulatedRing()
        values = []
        firmware.attach(
            {
                UUID_HR_MEASUREMENT: lambda _c, data: values.append(("hr", bytes(data))),
                "00002a19-0000-1000-8000-00805f9b34fb": lambda _c, data: values.append(("bat", bytes(data))),
            }
        )
        firmware.push_heart_rate(72, (800, 820))
        firmware.push_battery(55)
        self.assertEqual(values[0][0], "hr")
        self.assertEqual(values[0][1][1], 72)
        self.assertEqual(values[1], ("bat", bytes([55])))
        self.assertEqual(firmware.profile["00002a19-0000-1000-8000-00805f9b34fb"], bytes([55]))


class TestFakeBleClient(unittest.IsolatedAsyncioTestCase):
    async def test_connect_read_write(self):
        firmware = SimulatedRing()
        client = FakeBleClient(firmware)
        await client.connect()
        self.assertTrue(client.is_connected)
        self.assertEqual(await client.request_mtu(517), 517)
        battery = await client.read_gatt_char("00002a19-0000-1000-8000-00805f9b34fb")
        self.assertEqual(battery, bytes([87]))
        await client.write_gatt_char("aae28f02-71b5-42a1-8c3c-f9cf6ac969d0", pack(CMD_GET_USER, bytes([0])))
        await client.disconnect()
        self.assertFalse(client.is_connected)


if __name__ == "__main__":
    unittest.main()
