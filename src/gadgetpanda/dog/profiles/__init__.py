"""Dog model registry."""

from __future__ import annotations

from gadgetpanda.dog.models import DogProfile
from gadgetpanda.dog.profiles import generic as generic_mod
from gadgetpanda.dog.profiles import x1 as x1_mod

_REGISTRY: dict[str, DogProfile] = {
    x1_mod.PROFILE.id: x1_mod.PROFILE,
    generic_mod.PROFILE.id: generic_mod.PROFILE,
}


def all_profiles() -> tuple[DogProfile, ...]:
    return tuple(_REGISTRY.values())


def by_id(model_id: str) -> DogProfile:
    key = model_id.strip().lower()
    if key not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY))
        raise KeyError(f"unknown dog model {model_id!r}; known: {known}")
    return _REGISTRY[key]


def match_advertisement(name: str | None, *, default: str = "generic") -> DogProfile:
    """Pick a profile from BLE local name; fall back to generic."""
    if name:
        upper = name.upper()
        for profile in _REGISTRY.values():
            if profile.id == "generic":
                continue
            for prefix in profile.name_prefixes:
                if prefix.upper() in upper:
                    return profile
    return by_id(default)


def register(profile: DogProfile) -> None:
    """Allow makers / tests to inject additional models at runtime."""
    _REGISTRY[profile.id] = profile
