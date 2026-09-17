from __future__ import annotations

from typing import Any

from gadgetpanda.models import brand_display_value


def encode_event(name: str, payload: Any) -> dict[str, Any] | None:
    """Turn a Ring event into a JSON-safe dashboard message."""
    if name == "info":
        return {"type": "info", "info": brand_display_value(dict(payload or {}))}
    if name == "battery":
        return {"type": "battery", "value": int(payload)}
    if name == "heart_rate":
        return {
            "type": "heart_rate",
            "bpm": payload.bpm,
            "rr": list(payload.rr_intervals),
            "source": getattr(payload, "source", "ble") or "ble",
        }
    if name == "hrv":
        return {
            "type": "hrv",
            "sdnn": payload.sdnn,
            "sdnn_ms": payload.sdnn_ms,
            "samples": payload.samples,
        }
    if name == "sport":
        return {
            "type": "sport",
            "steps": payload.steps,
            "distance_m": payload.distance_m,
            "calories_kcal": payload.calories_kcal,
        }
    if name == "health":
        return {
            "type": "health",
            "vo2max": payload.vo2max,
            "breath_rate": payload.breath_rate,
            "emotion": payload.emotion,
            "stress": payload.stress,
            "stamina": payload.stamina,
        }
    if name == "temperature":
        return {
            "type": "temperature",
            "ambient_c": payload.ambient_c,
            "wrist_c": payload.wrist_c,
            "body_c": payload.body_c,
        }
    if name == "spo2":
        return {
            "type": "spo2",
            "spo2": payload.spo2,
            "on_wrist": payload.on_wrist,
            "enabled": payload.enabled,
        }
    if name == "optical_contact":
        return {"type": "optical_contact", "on_wrist": bool(payload)}
    if name == "imu" and payload:
        peak = max(payload, key=lambda item: item.gyro_mag2)
        first = payload[0]
        return {
            "type": "imu",
            "acc": [first.acc_x, first.acc_y, first.acc_z],
            "gyro": [peak.gyro_x, peak.gyro_y, peak.gyro_z],
        }
    if name == "ppg" and payload:
        return {
            "type": "ppg",
            "values": [sample.value for sample in payload],
            "flag": payload[0].flag,
        }
    if name == "user_info":
        return {
            "type": "user",
            "age": payload.age,
            "sex": payload.sex,
            "weight_kg": payload.weight_kg,
            "height_cm": payload.height_cm,
            "user_id": payload.user_id,
        }
    if name == "connected":
        ring = payload
        return {
            "type": "connected",
            "name": getattr(ring, "name", ""),
            "address": getattr(ring, "address", ""),
            "battery": getattr(ring, "battery", None),
        }
    if name == "disconnected":
        return {"type": "disconnected"}
    return None


def encode_snapshot(ring: Any) -> list[dict[str, Any]]:
    """Flatten the latest cached ring values for a newly opened browser."""
    messages: list[dict[str, Any]] = []
    mapping = (
        ("info", getattr(ring, "info", None)),
        ("battery", getattr(ring, "battery", None)),
        ("heart_rate", getattr(ring, "heart_rate", None)),
        ("hrv", getattr(ring, "hrv", None)),
        ("sport", getattr(ring, "sport", None)),
        ("health", getattr(ring, "health", None)),
        ("temperature", getattr(ring, "temperature", None)),
        ("spo2", getattr(ring, "spo2", None)),
        ("user_info", getattr(ring, "user", None)),
        ("imu", getattr(ring, "imu", None)),
        ("ppg", getattr(ring, "ppg", None)),
    )
    for name, payload in mapping:
        if payload is None or payload == {}:
            continue
        encoded = encode_event(name, payload)
        if encoded:
            messages.append(encoded)
    return messages
