from gadgetpanda.dashboard.payload import encode_event, encode_snapshot
from gadgetpanda.dashboard.server import _profile_int
from gadgetpanda.models import BloodOxygen, Health, HeartRate, Hrv, PpgSample, Raw6D, Sport, Temperature, UserInfo


def test_encode_heart_rate_and_hrv():
    heart = encode_event("heart_rate", HeartRate(bpm=72, rr_intervals=(800, 820)))
    assert heart == {"type": "heart_rate", "bpm": 72, "rr": [800, 820], "source": "ble"}
    estimated = encode_event("heart_rate", HeartRate(bpm=68, source="ppg"))
    assert estimated["source"] == "ppg"
    hrv = encode_event("hrv", Hrv(sdnn=12.5, sdnn_ms=12.2, samples=29))
    assert hrv["sdnn_ms"] == 12.2


def test_encode_grouped_sensors():
    sport = encode_event("sport", Sport(steps=1840, distance_m=125.0, calories_kcal=3.7))
    assert sport["steps"] == 1840
    health = encode_event("health", Health(vo2max=42, breath_rate=16, emotion=3, stress=4, stamina=80))
    assert health["stamina"] == 80
    temp = encode_event("temperature", Temperature(ambient_c=26.5, wrist_c=31.2, body_c=36.6))
    assert temp["body_c"] == 36.6
    spo2 = encode_event("spo2", BloodOxygen(enabled=True, spo2=98, on_wrist=True))
    assert spo2["on_wrist"] is True


def test_encode_imu_uses_peak_gyro():
    samples = (
        Raw6D(10, 20, 30, 0, 0, 0),
        Raw6D(11, 21, 31, 3, 4, 12),
    )
    message = encode_event("imu", samples)
    assert message["acc"] == [10, 20, 30]
    assert message["gyro"] == [3, 4, 12]


def test_encode_ppg_and_branded_info():
    from gadgetpanda.models import oem_vendor_mark

    message = encode_event("ppg", (PpgSample(flag=1, value=1200), PpgSample(flag=1, value=1210)))
    assert message["values"] == [1200, 1210]
    info = encode_event("info", {"vendor": oem_vendor_mark(), "model": "RL503"})
    assert info["info"]["vendor"] == "gadgetpanda"
    assert info["info"]["model"] == "RING503PANDA"


def test_encode_user_profile():
    message = encode_event("user_info", UserInfo(age=32, sex=0, weight_kg=58, height_cm=162, user_id=81))
    assert message["age"] == 32
    assert message["weight_kg"] == 58
    assert message["height_cm"] == 162


def test_profile_int_rejects_out_of_range():
    assert _profile_int("28", 1, 120, "อายุ") == 28
    try:
        _profile_int(300, 80, 250, "ส่วนสูง")
    except ValueError as exc:
        assert "ส่วนสูง" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_encode_snapshot_skips_empty():
    class Dummy:
        info = {"vendor": "gadgetpanda"}
        battery = 44
        heart_rate = HeartRate(bpm=68)
        hrv = None
        sport = None
        health = None
        temperature = None
        spo2 = None
        imu = None
        ppg = None

    messages = encode_snapshot(Dummy())
    types = [item["type"] for item in messages]
    assert types == ["info", "battery", "heart_rate"]
