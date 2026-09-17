"""Fine-grained soft-license feature catalog.

This is an honor-system entitlement layer (not DRM). Anyone with the MIT
source can remove checks; the goal is signed keys, device binding, and
clear product packaging for makers who opt in.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Feature:
    id: str
    group: str
    label: str
    description: str


FEATURES: tuple[Feature, ...] = (
    # Ring
    Feature("ring.scan", "ring", "Ring scan", "BLE scan / find RING503PANDA"),
    Feature("ring.connect", "ring", "Ring connect", "GATT connect / disconnect"),
    Feature("ring.stream", "ring", "Ring realtime", "Realtime sensor stream"),
    Feature("ring.ppg", "ring", "Ring PPG", "PPG-only streaming"),
    Feature("ring.imu", "ring", "Ring IMU", "Accelerometer / gyro frames"),
    Feature("ring.hr", "ring", "Ring heart rate", "Heart rate + HRV events"),
    Feature("ring.health", "ring", "Ring health pack", "Sport / health / SpO2 / temp"),
    Feature("ring.user", "ring", "Ring user profile", "Read/write wearer profile"),
    Feature("ring.ui", "ring", "Ring dashboard UI", "Local web dashboard"),
    # Dog
    Feature("dog.scan", "dog", "Dog scan", "BLE scan SoftDog / X1"),
    Feature("dog.connect", "dog", "Dog connect", "GATT connect + shell"),
    Feature("dog.action", "dog", "Dog actions", "Discrete action verbs"),
    Feature("dog.move", "dog", "Dog move", "Directional move / hold"),
    Feature("dog.program", "dog", "Dog program", "Program queue / play"),
    Feature("dog.raw", "dog", "Dog raw", "Raw GATT writes"),
    Feature("dog.ui", "dog", "Dog remote UI", "Web remote control"),
    # Drone
    Feature("drone.scan", "drone", "Drone scan", "Probe craft gateway"),
    Feature("drone.connect", "drone", "Drone connect", "UDP stick loop"),
    Feature("drone.stick", "drone", "Drone stick", "Axis / named stick"),
    Feature("drone.cmd", "drone", "Drone commands", "Takeoff / land / emergency"),
    Feature("drone.raw", "drone", "Drone raw", "Raw UDP payloads"),
    Feature("drone.wifi", "drone", "Drone Wi‑Fi join", "Force OS Wi‑Fi association"),
    Feature("drone.ui", "drone", "Drone FPV UI", "Web remote"),
    Feature("drone.rtsp", "drone", "Drone RTSP", "Camera preview proxy"),
    # Extras
    Feature("mqtt.bridge", "extra", "MQTT bridge", "Publish sensors to MQTT"),
    Feature("gesture", "extra", "Gesture helpers", "MotionWatch / gesture hooks"),
)

FEATURE_IDS: frozenset[str] = frozenset(f.id for f in FEATURES)
FEATURES_BY_ID: dict[str, Feature] = {f.id: f for f in FEATURES}

# Convenience packs the portal can offer as presets
PRESETS: dict[str, frozenset[str]] = {
    "ring_basic": frozenset(
        {
            "ring.scan",
            "ring.connect",
            "ring.stream",
            "ring.hr",
            "ring.health",
            "ring.ui",
        }
    ),
    "ring_full": frozenset(f.id for f in FEATURES if f.group == "ring"),
    "dog_full": frozenset(f.id for f in FEATURES if f.group == "dog"),
    "drone_full": frozenset(f.id for f in FEATURES if f.group == "drone"),
    "maker_all": frozenset(FEATURE_IDS),
}


def validate_features(features: list[str] | set[str] | frozenset[str]) -> frozenset[str]:
    unknown = set(features) - FEATURE_IDS
    if unknown:
        raise ValueError(f"unknown features: {sorted(unknown)}")
    return frozenset(features)


def features_by_group() -> dict[str, list[Feature]]:
    grouped: dict[str, list[Feature]] = {}
    for feature in FEATURES:
        grouped.setdefault(feature.group, []).append(feature)
    return grouped
