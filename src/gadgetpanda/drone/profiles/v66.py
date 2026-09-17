"""V66 / KY UFO style Wi‑Fi mini drone."""

from gadgetpanda.drone.profiles.base import V66_CAPABILITIES, wifi_profile

PROFILE = wifi_profile(
    id="v66",
    display_name="V66 Wi‑Fi drone",
    capabilities=V66_CAPABILITIES,
    frame_variant="tc",
    stick_deflection=40,
)
