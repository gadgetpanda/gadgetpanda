"""Fallback profile: GATT only — makers fill opcodes themselves."""

from __future__ import annotations

from gadgetpanda.dog.capabilities import Capability
from gadgetpanda.dog.profiles.base import gatt_profile

PROFILE = gatt_profile(
    model_id="generic",
    display_name="Generic GATT dog",
    name_prefixes=(),
    capabilities=frozenset({Capability.TRANSPORT_GATT}),
)
