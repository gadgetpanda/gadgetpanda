"""Built-in Wi‑Fi drone profiles."""

from __future__ import annotations

from gadgetpanda.drone.models import DroneProfile
from gadgetpanda.drone.profiles.base import V66_CAPABILITIES, wifi_profile
from gadgetpanda.drone.profiles.flow import PROFILE as FLOW
from gadgetpanda.drone.profiles.generic import PROFILE as GENERIC
from gadgetpanda.drone.profiles.v66 import PROFILE as V66

_REGISTRY: dict[str, DroneProfile] = {
    FLOW.id: FLOW,
    V66.id: V66,
    GENERIC.id: GENERIC,
}


def all_profiles() -> list[DroneProfile]:
    return list(_REGISTRY.values())


def by_id(model_id: str) -> DroneProfile:
    key = (model_id or "").strip().lower()
    aliases = {"flow-ufo": "flow", "kyufo": "flow", "ky-ufo": "flow"}
    key = aliases.get(key, key)
    if key not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY))
        raise KeyError(f"unknown drone model {model_id!r} — try: {known}")
    return _REGISTRY[key]


def register(profile: DroneProfile) -> None:
    _REGISTRY[profile.id] = profile


def match_ssid(ssid: str | None) -> DroneProfile | None:
    """Pick a profile from the craft AP name when possible."""
    if not ssid:
        return None
    upper = ssid.upper()
    if "FLOW" in upper:
        return FLOW
    if "KY" in upper and "UFO" in upper:
        return FLOW
    if "UFO" in upper or "V66" in upper:
        return V66
    return None


__all__ = [
    "FLOW",
    "GENERIC",
    "V66",
    "V66_CAPABILITIES",
    "all_profiles",
    "by_id",
    "match_ssid",
    "register",
    "wifi_profile",
]
