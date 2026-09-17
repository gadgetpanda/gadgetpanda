"""Shared helpers for dog model profiles."""

from __future__ import annotations

from gadgetpanda.dog.capabilities import Capability
from gadgetpanda.dog.models import DogProfile, GattUuids
from gadgetpanda.dog.protocol import remote_opcodes

X1_CAPABILITIES: frozenset[Capability] = frozenset(
    {
        Capability.TRANSPORT_GATT,
        Capability.MOVE_BASIC,
        Capability.POSE_SIT,
        Capability.POSE_LIE,
        Capability.POSE_HANDSTAND,
        Capability.POSE_JUMP,
        Capability.POSE_ROLL,
        Capability.POSE_DANCE,
        Capability.POSE_SWIM,
        Capability.POSE_PUSH_UPS,
        Capability.POSE_KUNG_FU,
        Capability.SOCIAL_GREET,
        Capability.SOCIAL_HANDSHAKE,
        Capability.SOCIAL_ACT_CUTE,
        Capability.SOCIAL_BLESS,
        Capability.SOCIAL_PEE,
        Capability.SOCIAL_LEARN,
        Capability.FX_SOUND,
        Capability.FX_VOICE,
        Capability.PROGRAM_SEQUENCE,
    }
)


def empty_opcodes() -> dict:
    return {}


def gatt_profile(
    *,
    model_id: str,
    display_name: str,
    name_prefixes: tuple[str, ...],
    capabilities: frozenset[Capability],
    opcodes: dict | None = None,
) -> DogProfile:
    return DogProfile(
        id=model_id,
        display_name=display_name,
        name_prefixes=name_prefixes,
        uuids=GattUuids(),
        capabilities=capabilities,
        opcodes=opcodes if opcodes is not None else empty_opcodes(),
    )


def x1_opcodes() -> dict:
    return remote_opcodes()
