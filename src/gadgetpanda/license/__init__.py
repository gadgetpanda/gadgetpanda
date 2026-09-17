"""Gadget Panda soft license (honor-system entitlements)."""

from gadgetpanda.license.client import (
    FeatureDenied,
    License,
    LicenseError,
    get_license,
    init,
    require,
    require_any,
)
from gadgetpanda.license.features import (
    FEATURE_IDS,
    FEATURES,
    FEATURES_BY_ID,
    PRESETS,
    features_by_group,
    validate_features,
)
from gadgetpanda.license.store import device_fingerprint

__all__ = [
    "FEATURE_IDS",
    "FEATURES",
    "FEATURES_BY_ID",
    "FeatureDenied",
    "License",
    "LicenseError",
    "PRESETS",
    "device_fingerprint",
    "features_by_group",
    "get_license",
    "init",
    "require",
    "require_any",
    "validate_features",
]
