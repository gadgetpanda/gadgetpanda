"""Shared profile helpers."""

from __future__ import annotations

from gadgetpanda.drone.capabilities import Capability
from gadgetpanda.drone.models import DroneProfile, TransportEndpoints

V66_CAPABILITIES = frozenset(
    {
        Capability.TRANSPORT_UDP,
        Capability.STICK,
        Capability.TAKEOFF,
        Capability.LAND,
        Capability.EMERGENCY,
        Capability.HEADLESS,
        Capability.CALIBRATE,
        Capability.LIGHT,
        Capability.HEARTBEAT,
    }
)


def wifi_profile(
    *,
    id: str,
    display_name: str,
    capabilities: frozenset[Capability],
    frame_variant: str = "tc",
    stick_deflection: int = 40,
    default_fixed_height: bool = False,
    host: str | None = None,
    udp_port: int | None = None,
) -> DroneProfile:
    endpoints = TransportEndpoints()
    if host is not None or udp_port is not None:
        endpoints = TransportEndpoints(
            host=host or endpoints.host,
            udp_port=udp_port or endpoints.udp_port,
        )
    return DroneProfile(
        id=id,
        display_name=display_name,
        endpoints=endpoints,
        capabilities=capabilities,
        frame_variant=frame_variant,
        stick_deflection=stick_deflection,
        default_fixed_height=default_fixed_height,
    )
