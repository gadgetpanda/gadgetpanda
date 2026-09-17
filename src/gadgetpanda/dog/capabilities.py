"""Capability flags for multi-model fun dogs."""

from __future__ import annotations

from enum import Enum, auto


class Capability(Enum):
    """What a concrete dog model can do."""

    TRANSPORT_GATT = auto()
    MOVE_BASIC = auto()

    POSE_SIT = auto()
    POSE_LIE = auto()
    POSE_HANDSTAND = auto()
    POSE_JUMP = auto()
    POSE_ROLL = auto()
    POSE_DANCE = auto()
    POSE_SWIM = auto()
    POSE_PUSH_UPS = auto()
    POSE_KUNG_FU = auto()

    SOCIAL_GREET = auto()
    SOCIAL_HANDSHAKE = auto()
    SOCIAL_ACT_CUTE = auto()
    SOCIAL_BLESS = auto()
    SOCIAL_PEE = auto()
    SOCIAL_LEARN = auto()

    FX_SOUND = auto()
    FX_VOICE = auto()

    PROGRAM_SEQUENCE = auto()


class UnsupportedCapability(Exception):
    """Raised when the selected model cannot perform the requested verb."""

    def __init__(self, model_id: str, capability: Capability):
        self.model_id = model_id
        self.capability = capability
        super().__init__(f"model {model_id!r} lacks capability {capability.name}")


class OpcodeUnknown(Exception):
    """Raised when the model has no BLE payload for this verb yet."""

    def __init__(self, model_id: str, verb: str):
        self.model_id = model_id
        self.verb = verb
        super().__init__(
            f"model {model_id!r} has no opcode for {verb!r} — "
            "use raw_write() or extend profiles/<model>.py"
        )
