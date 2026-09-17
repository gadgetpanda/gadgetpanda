"""FLOW-UFO / KY UFO GL stack — long stick frames (device ids 90–100)."""

from gadgetpanda.drone.profiles.base import V66_CAPABILITIES, wifi_profile

PROFILE = wifi_profile(
    id="flow",
    display_name="FLOW-UFO Wi‑Fi drone",
    capabilities=V66_CAPABILITIES,
    frame_variant="gl",
    stick_deflection=40,
    default_fixed_height=True,
)
