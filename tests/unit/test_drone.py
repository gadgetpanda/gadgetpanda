"""Unit tests for Wi‑Fi drone frames + client."""

from __future__ import annotations

import pytest

from gadgetpanda.drone import Drone, Stick, by_id
from gadgetpanda.drone.protocol import StickState, build_stick_frame, build_tc_body


def test_v66_profile():
    profile = by_id("v66")
    assert profile.frame_variant == "tc"
    assert profile.endpoints.udp_port == 7099


def test_tc_hover_frame():
    body = build_tc_body(StickState())
    assert body[0] == 0x66
    assert body[-1] == 0x99
    assert body[1:5] == bytes([128, 128, 128, 128])
    assert body[6] == body[1] ^ body[2] ^ body[3] ^ body[4] ^ body[5]
    wrapped = build_stick_frame(StickState(), variant="tc", udp_wrap=True)
    assert wrapped[0] == 0x03
    assert wrapped[1:] == body


def test_flow_gl_hover_enables_fixed_height_by_default():
    profile = by_id("flow")
    assert profile.frame_variant == "gl"
    assert profile.default_fixed_height is True
    frame = build_stick_frame(StickState(fixed_height=True), variant="gl", udp_wrap=True)
    # 03 66 14 80 80 80 80 00 02 … 02 99
    assert frame[:9] == bytes([0x03, 0x66, 0x14, 0x80, 0x80, 0x80, 0x80, 0x00, 0x02])
    assert frame[-1] == 0x99
    assert frame[-2] == 0x80 ^ 0x80 ^ 0x80 ^ 0x80 ^ 0x00 ^ 0x02


@pytest.mark.asyncio
async def test_flow_demo_connect_sets_fixed_height():
    async with Drone(model="flow", demo=True) as drone:
        assert drone.state.fixed_height is True
        await drone._send_stick()
        assert drone.last_tx is not None
        assert drone.last_tx[8] == 0x02  # F2 fixed-height bit


@pytest.mark.asyncio
async def test_drone_demo_stick_and_command():
    async with Drone(model="v66", demo=True) as drone:
        assert drone.connected
        await drone.stick(Stick.FORWARD)
        await drone._send_stick()
        assert drone.last_tx is not None
        assert drone.last_tx[0] == 0x03
        assert drone.last_tx[1] == 0x66
        assert drone.last_tx[3] > 128
        await drone.command("stop")
