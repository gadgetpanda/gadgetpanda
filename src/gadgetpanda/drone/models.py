"""Data models for the Wi‑Fi drone host."""

from __future__ import annotations

from dataclasses import dataclass, field

from gadgetpanda.drone.capabilities import Capability
from gadgetpanda.drone.protocol import DEFAULT_HOST, DEFAULT_RTSP, DEFAULT_UDP_PORT
from gadgetpanda.models import EventBus, Handler


@dataclass(frozen=True)
class TransportEndpoints:
    host: str = DEFAULT_HOST
    udp_port: int = DEFAULT_UDP_PORT
    rtsp_url: str = DEFAULT_RTSP


@dataclass(frozen=True)
class AdvertisedDrone:
    host: str
    udp_port: int = DEFAULT_UDP_PORT
    reachable: bool = False
    note: str = ""

    @property
    def address(self) -> str:
        return f"{self.host}:{self.udp_port}"

    @property
    def display_name(self) -> str:
        status = "up" if self.reachable else "unknown"
        return f"{self.host}:{self.udp_port} [{status}]" + (f" — {self.note}" if self.note else "")


@dataclass(frozen=True)
class DroneProfile:
    id: str
    display_name: str
    endpoints: TransportEndpoints = field(default_factory=TransportEndpoints)
    capabilities: frozenset[Capability] = field(default_factory=frozenset)
    frame_variant: str = "tc"  # tc | gl
    stick_deflection: int = 40
    # FLOW/GL defaults to altitude hold on connect.
    default_fixed_height: bool = False

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities


__all__ = [
    "AdvertisedDrone",
    "DroneProfile",
    "EventBus",
    "Handler",
    "TransportEndpoints",
]
