"""X1 SmartDog profile (shared across common color skins)."""

from __future__ import annotations

from gadgetpanda.dog.profiles.base import X1_CAPABILITIES, gatt_profile, x1_opcodes

PROFILE = gatt_profile(
    model_id="x1",
    display_name="X1 SmartDog",
    name_prefixes=("X1", "FY", "小智狗", "新鸿洋"),
    capabilities=X1_CAPABILITIES,
    opcodes=x1_opcodes(),
)
