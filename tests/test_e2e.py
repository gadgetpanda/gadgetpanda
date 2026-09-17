import pytest

from gadgetpanda import Ring
from gadgetpanda.cli import cmd_scan
from gadgetpanda.gesture import MotionWatch
from gadgetpanda.models import AdvertisedRing, Raw6D
from gadgetpanda.protocol import CMD_SET_UTC, increment_mac, pack
from gadgetpanda.ring import wait_until
from gadgetpanda.testing import FakeBleClient, SimulatedRing

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_scan_find_and_connect_profile(firmware: SimulatedRing, ring: Ring):
    async def discover(_timeout: float):
        return [
            AdvertisedRing("Watch X", "11:22:33:44:55:66", -30),
            firmware.advertised(),
        ]

    found = await Ring.scan(discover=discover)
    assert [item.address for item in found] == [firmware.address]

    located = await Ring.find(discover=discover, transport=FakeBleClient(firmware))
    assert located.address == firmware.address

    connected = []
    info = []
    battery = []
    ring.on("connected", connected.append)
    ring.on("info", info.append)
    ring.on("battery", battery.append)

    await ring.connect()
    try:
        assert ring.connected
        assert connected
        assert ring.info["model"] == "RING503PANDA"
        assert ring.info["vendor"] == "gadgetpanda"
        assert ring.battery == 87
        assert battery == [87]
        assert any(packet[2] == CMD_SET_UTC for packet in firmware.tx_log)
    finally:
        await ring.disconnect()
        assert not ring.connected


@pytest.mark.asyncio
async def test_realtime_sensors_end_to_end(ring: Ring, firmware: SimulatedRing):
    sport = []
    health = []
    temperature = []
    spo2 = []
    heart = []
    ring.on("sport", sport.append)
    ring.on("health", health.append)
    ring.on("temperature", temperature.append)
    ring.on("spo2", spo2.append)
    ring.on("heart_rate", heart.append)

    async with ring:
        await ring.get_sport()
        await ring.get_health()
        await ring.get_temperature()
        await ring.set_spo2(True)
        firmware.push_heart_rate(72)
        await wait_until(lambda: sport and health and temperature and spo2 and heart)

    assert sport[0].steps == 1840
    assert sport[0].distance_m == 125.0
    assert sport[0].calories_kcal == 3.7
    assert health[0].vo2max == 42
    assert temperature[0].body_c == 36.6
    assert spo2[0].spo2 == 98 and spo2[0].on_wrist
    assert heart[0].bpm == 72


@pytest.mark.asyncio
async def test_start_realtime_fills_every_live_value(ring: Ring, firmware: SimulatedRing):
    async with ring:
        firmware.push_heart_rate(72)
        await ring.start_realtime(interval=0.2)
        await wait_until(
            lambda: all(
                (
                    ring.sport,
                    ring.health,
                    ring.temperature,
                    ring.ppg,
                    ring.imu,
                    ring.heart_rate,
                    ring.battery is not None,
                )
            )
        )
        assert firmware.raw_enabled
        snap = ring.snapshot()
        await ring.stop_realtime()

    assert snap["sport"].steps == 1840
    assert snap["health"].vo2max == 42
    assert snap["temperature"].body_c == 36.6
    assert snap["ppg"][0].value == 1200
    assert snap["heart_rate"].bpm == 72
    assert snap["battery"] == 87


@pytest.mark.asyncio
async def test_vitals_stream_reads_spo2(ring: Ring, firmware: SimulatedRing):
    async with ring:
        await ring.apply_stream("vitals", interval=0.2)
        await wait_until(lambda: ring.spo2 is not None)
        assert not firmware.raw_enabled
        assert ring.spo2.spo2 == 98


@pytest.mark.asyncio
async def test_apply_stream_switches_hr_source(ring: Ring, firmware: SimulatedRing):
    ble = []
    ring.on("heart_rate", ble.append)
    async with ring:
        await ring.apply_stream("hr", interval=0.2)
        firmware.push_heart_rate(77)
        await wait_until(lambda: ring.heart_rate and ring.heart_rate.bpm == 77)
        assert ring.stream_mode == "hr"
        assert ring.hr_source == "ble"
        ble.clear()
        await ring.apply_stream("ppg", interval=0.2)
        firmware.push_heart_rate(91)
        await wait_until(lambda: ring.stream_mode == "ppg")
        assert ring.hr_source == "ppg"
        assert all(item.bpm != 91 for item in ble)


@pytest.mark.asyncio
async def test_hrv_emits_after_rr_window(ring: Ring, firmware: SimulatedRing):
    seen = []
    ring.on("hrv", seen.append)
    async with ring:
        for _ in range(30):
            firmware.push_heart_rate(72, rr=(800, 820))
        await wait_until(lambda: bool(seen))
    assert ring.hrv is not None
    assert seen[-1].sdnn_ms > 0
    assert ring.heart_rate.rr_intervals == (800, 820)


@pytest.mark.asyncio
async def test_user_and_history_end_to_end(ring: Ring):
    users = []
    birthdays = []
    sports = []
    sleeps = []
    sleep_done = []
    healths = []
    health_done = []
    hours = []
    hr_done = []
    ppg_done = []
    ring.on("user_info", users.append)
    ring.on("birthday", birthdays.append)
    ring.on("sport_history", sports.append)
    ring.on("sleep_history_chunk", sleeps.append)
    ring.on("sleep_history_complete", lambda *_args, **_kw: sleep_done.append(True))
    ring.on("health_history", healths.append)
    ring.on("health_history_complete", lambda *_args, **_kw: health_done.append(True))
    ring.on("heart_rate_history", hours.append)
    ring.on("heart_rate_history_complete", lambda *_args, **_kw: hr_done.append(True))
    ring.on("ppg_history_complete", lambda *_args, **_kw: ppg_done.append(True))

    async with ring:
        await ring.get_user()
        await ring.get_birthday()
        await ring.get_sport_history()
        await ring.get_sleep_history()
        await ring.get_health_history(0)
        await ring.get_heart_rate_history(0)
        await ring.get_ppg_history(0)
        await wait_until(
            lambda: users
            and birthdays
            and sports
            and sleeps
            and sleep_done
            and healths
            and health_done
            and hours
            and hr_done
            and ppg_done
        )

    assert users[0].age == 28 and users[0].user_id == 81
    assert birthdays[0].year == 1998 and birthdays[0].day == 20
    assert sports[0][0].steps == 900
    assert sleeps[0][0].actions == (8, 25)
    assert healths[0].heart_rate == 72
    assert hours[0][0].bpm == 74


@pytest.mark.asyncio
async def test_set_user_age_weight_height(ring: Ring, firmware: SimulatedRing):
    seen = []
    ring.on("user_info", seen.append)
    async with ring:
        await ring.get_user()
        await wait_until(lambda: ring.user is not None)
        await ring.set_user(32, None, 78, 182)
        await wait_until(lambda: ring.user and ring.user.age == 32)
    assert firmware.user["age"] == 32
    assert firmware.user["weight_kg"] == 78
    assert firmware.user["height_cm"] == 182
    assert firmware.user["sex"] == 1
    assert firmware.user["user_id"] == 81
    assert seen[-1].age == 32


@pytest.mark.asyncio
async def test_raw_imu_stream_and_gesture(ring: Ring):
    frames = []
    imu = []
    status = []
    ppg = []
    ring.on("raw", frames.append)
    ring.on("imu", imu.append)
    ring.on("ppg", ppg.append)
    ring.on("raw_status", status.append)

    async with ring:
        await ring.set_raw_enabled(True)
        await wait_until(lambda: frames and imu and ppg and status)

    assert status[-1] is True
    sample = frames[0].imu[0]
    assert sample.acc_x == 400
    assert frames[0].ppg[0].value == 1200
    assert ppg[0][0].value == 1200
    watch = MotionWatch(tap_threshold=50)
    watch.feed((sample,))
    assert watch.feed((Raw6D(20000, 0, 0, 0, 0, 0),)) == ["tap"]


@pytest.mark.asyncio
async def test_dfu_restore_and_write_guard(ring: Ring, firmware: SimulatedRing):
    with pytest.raises(RuntimeError, match="not connected"):
        await ring.get_sport()

    async with ring:
        address = await ring.enter_dfu()
        await ring.restore()
        assert address == increment_mac(firmware.address)
        assert firmware.tx_log[-1] == pack(0xF3)


@pytest.mark.asyncio
async def test_cli_scan_prints_simulated_ring(firmware: SimulatedRing, capsys, monkeypatch):
    async def fake_scan(timeout: float = 8.0, **_kwargs):
        return [firmware.advertised()]

    monkeypatch.setattr(Ring, "scan", fake_scan)
    await cmd_scan(timeout=0.1)
    out = capsys.readouterr().out
    assert firmware.address in out
    assert "RING503PANDA-E2E" in out


@pytest.mark.asyncio
async def test_find_without_ring_raises():
    async def discover(_timeout: float):
        return [AdvertisedRing("AirPods", "00:00:00:00:00:01", -20)]

    with pytest.raises(TimeoutError, match="ไม่พบแหวน"):
        await Ring.find(discover=discover)
