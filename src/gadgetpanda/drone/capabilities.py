"""Capability flags for Wi‑Fi drone profiles."""

from __future__ import annotations

from enum import Enum


class Capability(str, Enum):
    TRANSPORT_UDP = "transport_udp"
    STICK = "stick"
    TAKEOFF = "takeoff"
    LAND = "land"
    EMERGENCY = "emergency"
    HEADLESS = "headless"
    CALIBRATE = "calibrate"
    LIGHT = "light"
    HEARTBEAT = "heartbeat"


class UnsupportedCapability(RuntimeError):
    """Raised when the selected profile cannot perform a verb."""
