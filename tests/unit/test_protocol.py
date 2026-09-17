from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from gadgetpanda.protocol import (
    CMD_GET_HEALTH,
    CMD_GET_SPORT,
    CMD_GET_TEMP,
    CMD_GET_USER,
    CMD_PPG_HISTORY_END,
    CMD_RAW,
    CMD_SET_SPO2,
    END_TAG,
    RX_RAW_STREAM,
    begin_utc_bytes,
    checksum,
    i16be,
    increment_mac,
    looks_like_ring,
    pack,
    pack_dfu,
    parse_ascii,
    parse_heart_rate,
    parse_rx,
    parse_system_id,
    restore_zone_utc,
    take_frames,
    u16be,
    u24be,
    u32be,
    u40be,
    u8,
    utc_bytes,
    utc_seconds,
)


class TestFrameCodec(unittest.TestCase):
    def test_pack_checksum_and_length(self):
        packet = pack(CMD_GET_SPORT)
        self.assertEqual(packet[0], 0xFF)
        self.assertEqual(packet[1], 4)
        self.assertEqual(packet[2], CMD_GET_SPORT)
        self.assertEqual(packet[3], checksum(packet[:3]))
        self.assertEqual(len(packet), 4)

    def test_pack_with_payload(self):
        packet = pack(CMD_RAW, bytes([1, 1]))
        self.assertEqual(packet[1], len(packet))
        self.assertEqual(packet[-1], checksum(packet[:-1]))

    def test_pack_dfu_shape(self):
        packet = pack_dfu()
        self.assertEqual(packet[0], 0xFF)
        self.assertEqual(packet[1], 4)
        self.assertEqual(packet[2], 0x27)
        self.assertEqual(len(packet), 4)

    def test_signed_checksum_with_high_bytes(self):
        body = bytes([0xFF, 5, 0x15, 0xC0])
        self.assertEqual(checksum(body), ((-sum(b - 256 if b > 127 else b for b in body)) ^ 0x3A) & 0xFF)


class TestNumbers(unittest.TestCase):
    def test_unsigned_readers(self):
        data = bytes([1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(u8(data, 0), 1)
        self.assertEqual(u16be(data, 0), 0x0102)
        self.assertEqual(u24be(data, 0), 0x010203)
        self.assertEqual(u32be(data, 0), 0x01020304)
        self.assertEqual(u40be(data, 0), 0x0102030405)

    def test_signed_i16(self):
        self.assertEqual(i16be((-400).to_bytes(2, "big", signed=True), 0), -400)


class TestIdentityHelpers(unittest.TestCase):
    def test_looks_like_ring_filters_and_aliases(self):
        self.assertTrue(looks_like_ring("RING503PANDA-0001"))
        self.assertTrue(looks_like_ring("RL503-E2E"))
        self.assertTrue(looks_like_ring("RL503N-ABC"))
        self.assertTrue(looks_like_ring("CL831"))
        self.assertFalse(looks_like_ring("AirPods"))
        self.assertFalse(looks_like_ring(None))

    def test_increment_mac(self):
        self.assertEqual(increment_mac("AA:BB:CC:DD:EE:FF"), "AA:BB:CC:DD:EE:00")
        self.assertEqual(increment_mac("AA:BB:CC:DD:EE:10"), "AA:BB:CC:DD:EE:11")

    def test_parse_ascii_and_system_id(self):
        from gadgetpanda.models import oem_vendor_mark

        oem = oem_vendor_mark()
        self.assertEqual(parse_ascii(oem.encode("ascii") + b"\x00"), oem)
        self.assertEqual(parse_system_id(b"\x01\x02"), "0102")


class TestHeartRateParser(unittest.TestCase):
    def test_uint8(self):
        sample = parse_heart_rate(bytes([0x00, 72]))
        self.assertEqual(sample.bpm, 72)
        self.assertEqual(sample.rr_intervals, ())
        self.assertIsNone(sample.contact)

    def test_with_rr_and_contact(self):
        sample = parse_heart_rate(bytes([0x16, 72, 0x20, 0x03, 0x40, 0x03]))
        self.assertEqual(sample.bpm, 72)
        self.assertTrue(sample.contact)
        self.assertEqual(sample.rr_intervals, (800, 832))

    def test_uint16_and_energy(self):
        sample = parse_heart_rate(bytes([0x09, 0x58, 0x02, 0x10, 0x00]))
        self.assertEqual(sample.bpm, 600)
        self.assertEqual(sample.energy_kj, 16)

    def test_too_short(self):
        with self.assertRaises(ValueError):
            parse_heart_rate(bytes([0x00]))


class TestTakeFrames(unittest.TestCase):
    def test_reassembly_across_chunks(self):
        packet = pack(CMD_GET_SPORT, (1840).to_bytes(3, "big") + (12500).to_bytes(3, "big") + (37).to_bytes(3, "big"))
        buf = bytearray()
        self.assertEqual(take_frames(buf, packet[:4]), [])
        frames = take_frames(buf, packet[4:])
        self.assertEqual(frames, [packet])

    def test_ignores_noise_before_sof(self):
        packet = pack(CMD_GET_HEALTH, bytes([42, 16, 3, 4, 80]))
        buf = bytearray()
        frames = take_frames(buf, b"\x00\x11" + packet)
        self.assertEqual(frames, [packet])


class TestParseRx(unittest.TestCase):
    def test_sport_health_temp_user(self):
        sport = parse_rx(pack(CMD_GET_SPORT, (1840).to_bytes(3, "big") + (12500).to_bytes(3, "big") + (37).to_bytes(3, "big")))[0]
        self.assertEqual(sport.name, "sport")
        self.assertEqual(sport.payload.steps, 1840)
        self.assertEqual(sport.payload.distance_m, 125.0)
        self.assertEqual(sport.payload.calories_kcal, 3.7)

        health = parse_rx(pack(CMD_GET_HEALTH, bytes([42, 16, 3, 4, 80])))[0]
        self.assertEqual(health.payload.vo2max, 42)
        self.assertEqual(health.payload.stamina, 80)

        temp = parse_rx(pack(CMD_GET_TEMP, (265).to_bytes(2, "big") + (312).to_bytes(2, "big") + (366).to_bytes(2, "big")))[0]
        self.assertEqual(temp.payload.body_c, 36.6)

        user = parse_rx(pack(CMD_GET_USER, bytes([0, 0, 28, 1, 70, 175]) + (81).to_bytes(5, "big")))[0]
        self.assertEqual(user.name, "user_info")
        self.assertEqual(user.payload.age, 28)
        self.assertEqual(user.payload.user_id, 81)

    def test_spo2_variants(self):
        short = parse_rx(pack(CMD_SET_SPO2))[0]
        self.assertFalse(short.payload.enabled)
        mid = parse_rx(pack(CMD_SET_SPO2, bytes([1, 0])))[0]
        self.assertTrue(mid.payload.enabled)
        full = parse_rx(pack(CMD_SET_SPO2, bytes([1, 98, 0, 0, 1])))[0]
        self.assertEqual(full.payload.spo2, 98)
        self.assertTrue(full.payload.on_wrist)

    def test_raw_stream(self):
        imu = (400).to_bytes(2, "big", signed=True) * 3 + (12).to_bytes(2, "big", signed=True) * 3
        ppg = (1200).to_bytes(3, "big")
        payload = bytes([3]) + (10).to_bytes(4, "big") + bytes([12]) + imu + bytes([3, 1]) + ppg
        event = parse_rx(pack(RX_RAW_STREAM, payload))[0]
        self.assertEqual(event.name, "raw")
        self.assertEqual(event.payload.imu[0].acc_x, 400)
        self.assertEqual(event.payload.imu[0].gyro_x, 12)
        self.assertEqual(event.payload.ppg[0].value, 1200)

    def test_ppg_history_end(self):
        events = parse_rx(pack(CMD_PPG_HISTORY_END, END_TAG.to_bytes(4, "big")))
        self.assertEqual(events[0].name, "ppg_history_complete")

    def test_unknown_and_invalid(self):
        self.assertEqual(parse_rx(b""), [])
        self.assertEqual(parse_rx(b"\x00\x04\x01\x00"), [])
        unknown = parse_rx(pack(0x55, b"\x01"))[0]
        self.assertEqual(unknown.name, "raw_command")
        self.assertEqual(unknown.extra["mode"], 0x55)


class TestTimeHelpers(unittest.TestCase):
    def test_utc_roundtrip_shape(self):
        when = datetime(2024, 1, 2, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
        stamp = utc_seconds(when, tz=ZoneInfo("UTC"))
        self.assertEqual(len(utc_bytes(when)), 4)
        self.assertEqual(len(begin_utc_bytes(stamp * 1000)), 4)
        ms = restore_zone_utc(stamp, tz=ZoneInfo("UTC"))
        self.assertEqual(ms, stamp * 1000)


if __name__ == "__main__":
    unittest.main()
