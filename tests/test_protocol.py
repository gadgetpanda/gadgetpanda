from gadgetpanda.protocol import (
    CMD_PPG_HISTORY_END,
    checksum,
    pack,
    parse_heart_rate,
    parse_rx,
    parse_system_id,
    looks_like_ring,
    take_frames,
)


def test_checksum_sport_query():
    packet = pack(0x15)
    assert packet[0] == 0xFF
    assert packet[1] == 4
    assert packet[2] == 0x15
    assert packet[3] == checksum(packet[:3])
    assert len(packet) == 4


def test_pack_roundtrip_length():
    payload = bytes([1, 1])
    packet = pack(0x98, payload)
    assert packet[1] == len(packet)
    assert packet[-1] == checksum(packet[:-1])


def test_parse_heart_rate_uint8():
    sample = parse_heart_rate(bytes([0x00, 72]))
    assert sample.bpm == 72
    assert sample.rr_intervals == ()


def test_parse_heart_rate_with_rr():
    sample = parse_heart_rate(bytes([0x10, 72, 0x20, 0x03, 0x40, 0x03]))
    assert sample.bpm == 72
    assert sample.rr_intervals == (800, 832)


def test_hrv_sdnn_and_tracker():
    from gadgetpanda.models import HrvTracker, calculate_hrv

    assert calculate_hrv([800, 800, 800]) == 0.0
    assert calculate_hrv([800, 820, 780]) > 0
    tracker = HrvTracker()
    assert tracker.feed(()) is None
    for _ in range(29):
        assert tracker.feed((800, 820)) is None
    hrv = tracker.feed((800, 820))
    assert hrv is not None
    assert hrv.samples == 29
    assert hrv.sdnn_ms > 0


def test_parse_user_info():
    # offsets 3-4 unused, 5 age, 6 sex, 7 weight, 8 height, 9-13 userId
    payload = bytes([0, 0, 28, 1, 70, 175, 0, 0, 0, 0, 1])
    packet = pack(0x03, payload)
    events = parse_rx(packet)
    assert events[0].name == "user_info"
    assert events[0].payload.age == 28
    assert events[0].payload.sex == 1
    assert events[0].payload.weight_kg == 70
    assert events[0].payload.height_cm == 175


def test_parse_sport():
    payload = (
        (1234).to_bytes(3, "big")
        + (5600).to_bytes(3, "big")
        + (89).to_bytes(3, "big")
    )
    packet = pack(0x15, payload)
    sport = parse_rx(packet)[0].payload
    assert sport.steps == 1234
    assert sport.distance_m == 56.0
    assert sport.calories_kcal == 8.9


def test_parse_raw_empty():
    payload = bytes(
        [
            7,  # frame
            0,
            0,
            0,
            1,  # stamp
            0,  # n6d
            0,  # nppg
        ]
    )
    packet = pack(0x99, payload)
    events = parse_rx(packet)
    assert events[0].name == "raw"
    assert events[0].payload.imu == ()
    assert events[0].payload.ppg == ()


def test_take_frames_reassembles_and_parse_rx_accepts_padding():
    packet = pack(0x15, (1).to_bytes(3, "big") * 3)
    events = parse_rx(packet + b"\x00\x00")
    assert events[0].name == "sport"
    buffer = bytearray()
    assert take_frames(buffer, packet[:6]) == []
    assert take_frames(buffer, packet[6:]) == [packet]


def test_ppg_history_end_on_0x93():
    packet = pack(CMD_PPG_HISTORY_END, (0xFFFFFFFF).to_bytes(4, "big"))
    events = parse_rx(packet)
    assert events[0].name == "ppg_history_complete"


def test_spo2_short_ack():
    events = parse_rx(pack(0x37, bytes([1])))
    assert events[0].name == "spo2"
    assert events[0].payload.enabled is True


def test_utc_ack_and_firmware_debug():
    utc = parse_rx(pack(0x08))
    assert utc[0].name == "utc"
    debug = parse_rx(pack(0x47, b"gh3026_process_start"))
    assert debug[0].name == "debug"
    assert "gh3026" in debug[0].payload


def test_parse_system_id_is_hex():
    assert parse_system_id(b"3DUfD3\"") == "33445566443322"


def test_name_filter():
    assert looks_like_ring("RL503-AABB")
    assert looks_like_ring("RL503N-XY9")
    assert looks_like_ring("RING503PANDA-AABB")
    assert looks_like_ring("RING503nPANDA-XY9")
    assert looks_like_ring("CL-9")
    assert not looks_like_ring("Watch")
    assert not looks_like_ring(None)


def test_panda_display_name():
    from gadgetpanda.models import panda_display_name

    mac = "AA:BB:CC:DD:EE:10"
    assert panda_display_name("RL503", mac) == "RING503PANDA-DEE10"
    assert panda_display_name("RL503-AB12C", mac) == "RING503PANDA-AB12C"
    assert panda_display_name("RL503N", mac) == "RING503nPANDA-DEE10"
    assert panda_display_name("RL503N-XY9", mac) == "RING503nPANDA-XY9"
    assert panda_display_name("RING503PANDA", mac) == "RING503PANDA-DEE10"
    assert panda_display_name("RING503nPANDA-XY9", mac) == "RING503nPANDA-XY9"
    assert panda_display_name("Watch", mac) == "Watch"


def test_brand_display_hides_oem_vendor():
    from gadgetpanda.models import brand_display, brand_display_value, oem_vendor_mark

    oem = oem_vendor_mark()
    assert brand_display(oem) == "gadgetpanda"
    assert brand_display(oem.title()) == "gadgetpanda"
    assert brand_display(f"vendor={oem.upper()}") == "vendor=gadgetpanda"
    assert brand_display_value({"vendor": oem}) == {"vendor": "gadgetpanda"}
    assert brand_display("RL503") == "RING503PANDA"
    assert brand_display("RL503N") == "RING503nPANDA"
    assert brand_display("model=RL503 / RL503N") == "model=RING503PANDA / RING503nPANDA"


def test_cli_print_hides_oem_vendor(capsys):
    from gadgetpanda.cli import _print
    from gadgetpanda.models import oem_vendor_mark

    oem = oem_vendor_mark()
    _print(f'info {{"vendor": "{oem}"}}')
    _print(f"error {oem.title()} BLE timeout")
    _print("model RL503 / RL503N")
    out = capsys.readouterr().out
    assert oem.lower() not in out.lower()
    assert "gadgetpanda" in out
    assert "error gadgetpanda BLE timeout" in out
    assert "RL503" not in out
    assert "RING503PANDA / RING503nPANDA" in out


def test_cli_print_imu_uses_peak_gyro(capsys):
    from gadgetpanda.cli import _print_imu
    from gadgetpanda.models import Raw6D

    _print_imu(
        (
            Raw6D(-128, 3520, -2240, 0, 0, 0),
            Raw6D(-100, 3400, -2000, 12, -4, 3),
        )
    )
    out = capsys.readouterr().out
    assert "gyro=(12,-4,3)" in out
    assert "gyros=(0,0,0) (12,-4,3)" in out


def test_parse_sex_aliases():
    from gadgetpanda.cli import parse_sex

    assert parse_sex("1") == 1
    assert parse_sex("ชาย") == 1
    assert parse_sex("male") == 1
    assert parse_sex("0") == 0
    assert parse_sex("หญิง") == 0


def test_user_sex_missing_value_is_clear(capsys):
    from gadgetpanda.cli import main

    try:
        main(["ring", "user", "--age", "32", "--weight", "78", "--height", "182", "--sex"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit")
    err = capsys.readouterr().err
    assert "--sex 1" in err or "ชาย" in err


def test_cli_print_ppg_values(capsys):
    from gadgetpanda.cli import _print_ppg
    from gadgetpanda.models import PpgSample

    _print_ppg((PpgSample(flag=1, value=1200), PpgSample(flag=1, value=1198)))
    out = capsys.readouterr().out
    assert "ppg flag=1 n=2 1200 1198" in out
