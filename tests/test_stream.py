from gadgetpanda.stream import allows_event, mode_payload, resolve_mode


def test_resolve_unknown_falls_back_to_all():
    assert resolve_mode("nope").id == "all"
    assert resolve_mode("ppg").hr == "ppg"
    assert resolve_mode("hr").raw is False


def test_allows_event_filters_by_mode():
    assert allows_event("hr", "heart_rate")
    assert allows_event("hr", "battery")
    assert not allows_event("hr", "ppg")
    assert allows_event("all", "imu")
    assert allows_event("ppg", "ppg")
    assert not allows_event("ppg", "sport")


def test_mode_payload_lists_choices():
    payload = mode_payload("vitals")
    assert payload["type"] == "mode"
    assert payload["mode"] == "vitals"
    assert payload["gets"]
    assert payload["needs"]
    assert payload["skips"]
    assert payload["flags"]["spo2"] is True
    assert payload["flags"]["raw"] is False
    assert [item["id"] for item in payload["modes"]] == ["all", "hr", "ppg", "vitals", "motion", "activity"]
    assert payload["modes"][0]["gets"]
