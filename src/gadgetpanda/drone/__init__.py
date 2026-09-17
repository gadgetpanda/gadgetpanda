"""Wi‑Fi fun-drone host (sibling to ring + dog). Default profile: V66 / KY UFO stack."""

from gadgetpanda.drone.actions import Command, Stick
from gadgetpanda.drone.capabilities import Capability, UnsupportedCapability
from gadgetpanda.drone.client import Drone
from gadgetpanda.drone.models import AdvertisedDrone, DroneProfile, TransportEndpoints
from gadgetpanda.drone.profiles import all_profiles, by_id, register
from gadgetpanda.drone.protocol import (
    CENTER,
    DEFAULT_HOST,
    DEFAULT_UDP_PORT,
    HEARTBEAT,
    STOP_CONTROL,
    build_stick_frame,
    wrap_udp,
)
from gadgetpanda.drone.testing import FakeDroneTransport, SimulatedDrone
from gadgetpanda.drone.wifi import WifiError, WifiStatus, ensure_joined, join as wifi_join, list_networks, status as wifi_status

__all__ = [
    "AdvertisedDrone",
    "CENTER",
    "Capability",
    "Command",
    "DEFAULT_HOST",
    "DEFAULT_UDP_PORT",
    "Drone",
    "DroneProfile",
    "FakeDroneTransport",
    "HEARTBEAT",
    "STOP_CONTROL",
    "SimulatedDrone",
    "Stick",
    "TransportEndpoints",
    "UnsupportedCapability",
    "WifiError",
    "WifiStatus",
    "all_profiles",
    "build_stick_frame",
    "by_id",
    "ensure_joined",
    "list_networks",
    "register",
    "wifi_join",
    "wifi_status",
    "wrap_udp",
]
