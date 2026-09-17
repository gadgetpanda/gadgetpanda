"""Data models for the dog host."""

from __future__ import annotations

from dataclasses import dataclass, field

from gadgetpanda.dog.actions import Action, Move
from gadgetpanda.dog.capabilities import Capability
from gadgetpanda.dog.protocol import UUID_NOTIFY, UUID_SERVICE, UUID_WRITE
from gadgetpanda.models import EventBus, Handler  # re-export pattern


@dataclass(frozen=True)
class AdvertisedDog:
    name: str
    address: str
    rssi: int | None = None

    @property
    def display_name(self) -> str:
        return self.name or self.address or "unknown"


@dataclass(frozen=True)
class GattUuids:
    service: str = UUID_SERVICE
    notify: str = UUID_NOTIFY
    write: str = UUID_WRITE


@dataclass(frozen=True)
class DogProfile:
    """Per-model capability + opcode table.

    ``opcodes`` keys are ``Action`` or ``Move`` members; values are raw GATT write
    payloads. Missing entries raise ``OpcodeUnknown``.
    """

    id: str
    display_name: str
    name_prefixes: tuple[str, ...] = ()
    uuids: GattUuids = field(default_factory=GattUuids)
    capabilities: frozenset[Capability] = field(default_factory=frozenset)
    opcodes: dict[Action | Move, bytes] = field(default_factory=dict)

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def opcode_for(self, verb: Action | Move) -> bytes | None:
        return self.opcodes.get(verb)


__all__ = [
    "AdvertisedDog",
    "DogProfile",
    "EventBus",
    "GattUuids",
    "Handler",
]
