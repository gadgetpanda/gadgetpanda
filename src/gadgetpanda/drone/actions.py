"""High-level verbs for the drone host."""

from __future__ import annotations

from enum import Enum


class Stick(str, Enum):
    """Named stick presets (relative to center 128)."""

    HOVER = "hover"
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    YAW_LEFT = "yaw_left"
    YAW_RIGHT = "yaw_right"


class Command(str, Enum):
    """One-shot / latched flag commands."""

    TAKEOFF = "takeoff"
    LAND = "land"
    STOP = "stop"
    EMERGENCY = "emergency"
    HEADLESS_ON = "headless_on"
    HEADLESS_OFF = "headless_off"
    CALIBRATE = "calibrate"
    LIGHT_ON = "light_on"
    LIGHT_OFF = "light_off"
