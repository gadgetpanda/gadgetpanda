"""Unit tests for gadgetpanda.dog."""

from __future__ import annotations

import unittest

from gadgetpanda.dog import (
    Action,
    Capability,
    Dog,
    Move,
    OpcodeUnknown,
    SimulatedDog,
    UnsupportedCapability,
    by_id,
    match_advertisement,
)
from gadgetpanda.dog.actions import ACTION_CAPABILITY
from gadgetpanda.dog.protocol import (
    PROGRAM_CLEAR,
    PROGRAM_ENTER,
    PROGRAM_EXIT_TO_REMOTE,
    PROGRAM_PLAY,
    program_opcodes,
    remote_opcodes,
)
from gadgetpanda.dog.testing import FakeDogBleClient


class ProfileTests(unittest.TestCase):
    def test_x1_has_voice_and_program(self):
        x1 = by_id("x1")
        self.assertIn(Capability.FX_VOICE, x1.capabilities)
        self.assertIn(Capability.PROGRAM_SEQUENCE, x1.capabilities)
        self.assertIn(Capability.TRANSPORT_GATT, x1.capabilities)

    def test_x1_remote_opcodes_complete(self):
        x1 = by_id("x1")
        self.assertEqual(x1.opcodes, remote_opcodes())
        self.assertEqual(x1.opcodes[Move.FORWARD], bytes([0xB1, 0x01, 0x00]))
        self.assertEqual(x1.opcodes[Action.JUMP], bytes([0xB1, 0x00, 0x0E]))

    def test_generic_is_raw_only(self):
        generic = by_id("generic")
        self.assertEqual(generic.capabilities, frozenset({Capability.TRANSPORT_GATT}))
        self.assertNotIn(Capability.POSE_SIT, generic.capabilities)

    def test_match_advertisement_x1(self):
        self.assertEqual(match_advertisement("X1-ABC").id, "x1")
        self.assertEqual(match_advertisement("FY-DOG").id, "x1")
        self.assertEqual(match_advertisement("新鸿洋小智狗").id, "x1")
        self.assertEqual(match_advertisement("unknown-bot").id, "generic")


class GateTests(unittest.IsolatedAsyncioTestCase):
    async def test_x1_opcodes(self):
        firmware = SimulatedDog()
        dog = Dog(firmware.advertised(), model="x1", transport=FakeDogBleClient(firmware))
        await dog.connect()
        await dog.move(Move.FORWARD)
        await dog.action(Action.VOICE)
        await dog.move(Move.STOP)
        self.assertEqual(
            firmware.tx_log,
            [bytes([0xB1, 0x01, 0x00]), bytes([0xB1, 0x00, 0x0C]), bytes([0xB1, 0x05, 0x00])],
        )
        await dog.disconnect()

    async def test_unsupported_on_generic(self):
        firmware = SimulatedDog(name="RAW")
        dog = Dog(firmware.advertised(), model="generic", transport=FakeDogBleClient(firmware))
        await dog.connect()
        with self.assertRaises(UnsupportedCapability) as ctx:
            await dog.action(Action.SIT_DOWN)
        self.assertEqual(ctx.exception.capability, ACTION_CAPABILITY[Action.SIT_DOWN])
        await dog.disconnect()

    async def test_raw_write_hex_and_bytes(self):
        firmware = SimulatedDog()
        dog = Dog(firmware.advertised(), model="x1", transport=FakeDogBleClient(firmware))
        received: list[bytes] = []
        dog.on("tx", received.append)
        await dog.connect()
        await dog.raw_write(bytes([0xAA, 0x55, 0x01]))
        await dog.raw_write("aa 55 02")
        self.assertEqual(firmware.tx_log, [bytes([0xAA, 0x55, 0x01]), bytes([0xAA, 0x55, 0x02])])
        self.assertEqual(received, firmware.tx_log)
        await dog.disconnect()

    async def test_notify_emits_rx(self):
        firmware = SimulatedDog()
        dog = Dog(firmware.advertised(), model="x1", transport=FakeDogBleClient(firmware))
        inbox: list[bytes] = []
        dog.on("rx", inbox.append)
        await dog.connect()
        firmware.push_rx(b"\x01\x02")
        self.assertEqual(inbox, [b"\x01\x02"])
        self.assertEqual(dog.last_rx, b"\x01\x02")
        await dog.disconnect()

    async def test_action_routes_move_name(self):
        from gadgetpanda.dog.models import DogProfile, GattUuids
        from gadgetpanda.dog.profiles.base import X1_CAPABILITIES

        profile = DogProfile(
            id="x1-test",
            display_name="X1 test",
            uuids=GattUuids(),
            capabilities=X1_CAPABILITIES,
            opcodes={Move.FORWARD: bytes([0x01])},
        )
        firmware = SimulatedDog()
        dog = Dog(firmware.advertised(), model=profile, transport=FakeDogBleClient(firmware))
        await dog.connect()
        await dog.action("forward")
        self.assertEqual(firmware.tx_log, [bytes([0x01])])
        await dog.disconnect()

    async def test_hold_move_then_stop(self):
        firmware = SimulatedDog()
        dog = Dog(firmware.advertised(), model="x1", transport=FakeDogBleClient(firmware))
        await dog.connect()
        await dog.hold_move(Move.FORWARD, seconds=0.12, interval=0.05)
        self.assertGreaterEqual(len(firmware.tx_log), 2)
        self.assertTrue(all(frame[:2] == bytes([0xB1, 0x01]) for frame in firmware.tx_log[:-1]))
        self.assertEqual(firmware.tx_log[-1], bytes([0xB1, 0x05, 0x00]))
        await dog.disconnect()

    async def test_run_program_sequence(self):
        firmware = SimulatedDog()
        dog = Dog(firmware.advertised(), model="x1", transport=FakeDogBleClient(firmware))
        await dog.connect()
        await dog.run_program([Action.JUMP, Action.SIT_DOWN], step_delay=0)
        self.assertEqual(
            firmware.tx_log,
            [
                PROGRAM_ENTER,
                PROGRAM_CLEAR,
                bytes([0xB2, 0x00, 0x0E]),
                bytes([0xB2, 0x00, 0x09]),
                PROGRAM_PLAY,
            ],
        )
        await dog.disconnect()

    async def test_program_rejects_remote_only_verb(self):
        firmware = SimulatedDog()
        dog = Dog(firmware.advertised(), model="x1", transport=FakeDogBleClient(firmware))
        await dog.connect()
        with self.assertRaises(OpcodeUnknown):
            await dog.program_add(Action.VOICE)
        await dog.disconnect()


class ProtocolTests(unittest.TestCase):
    def test_parse_hex(self):
        from gadgetpanda.dog.protocol import parse_hex_payload

        self.assertEqual(parse_hex_payload("aa:bb-01"), bytes([0xAA, 0xBB, 0x01]))
        with self.assertRaises(ValueError):
            parse_hex_payload("abc")

    def test_mode_frames(self):
        self.assertEqual(PROGRAM_ENTER, bytes([0xB2, 0xFF, 0xFF]))
        self.assertEqual(PROGRAM_EXIT_TO_REMOTE, bytes([0xB2, 0xFF, 0xFE]))
        self.assertEqual(PROGRAM_PLAY, bytes([0xB2, 0xFF, 0xF1]))
        self.assertEqual(PROGRAM_CLEAR, bytes([0xB2, 0xFF, 0xF2]))
        self.assertEqual(program_opcodes()[Action.JUMP], bytes([0xB2, 0x00, 0x0E]))
        self.assertNotIn(Action.VOICE, program_opcodes())


if __name__ == "__main__":
    unittest.main()
