"""Generic UDP drone — stick + raw only."""

from gadgetpanda.drone.capabilities import Capability
from gadgetpanda.drone.profiles.base import wifi_profile

PROFILE = wifi_profile(
    id="generic",
    display_name="Generic Wi‑Fi drone",
    capabilities=frozenset(
        {
            Capability.TRANSPORT_UDP,
            Capability.STICK,
            Capability.HEARTBEAT,
        }
    ),
    frame_variant="tc",
)
