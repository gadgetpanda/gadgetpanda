"""Multi-model fun-dog BLE host (sibling to the RING503PANDA ring stack)."""

from gadgetpanda.dog.actions import Action, Move
from gadgetpanda.dog.capabilities import Capability, OpcodeUnknown, UnsupportedCapability
from gadgetpanda.dog.client import Dog
from gadgetpanda.dog.models import AdvertisedDog, DogProfile, GattUuids
from gadgetpanda.dog.profiles import all_profiles, by_id, match_advertisement, register
from gadgetpanda.dog.protocol import (
    PROGRAM_CLEAR,
    PROGRAM_ENTER,
    PROGRAM_EXIT_TO_REMOTE,
    PROGRAM_PLAY,
    PROGRAM_VERBS,
    remote_opcodes,
)
from gadgetpanda.dog.testing import FakeDogBleClient, SimulatedDog

__all__ = [
    "Action",
    "AdvertisedDog",
    "Capability",
    "Dog",
    "DogProfile",
    "FakeDogBleClient",
    "GattUuids",
    "Move",
    "OpcodeUnknown",
    "PROGRAM_CLEAR",
    "PROGRAM_ENTER",
    "PROGRAM_EXIT_TO_REMOTE",
    "PROGRAM_PLAY",
    "PROGRAM_VERBS",
    "SimulatedDog",
    "UnsupportedCapability",
    "all_profiles",
    "by_id",
    "match_advertisement",
    "register",
    "remote_opcodes",
]
