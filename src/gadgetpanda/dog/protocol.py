"""BLE constants + frame builders for SmartDog-style GATT toys.

Remote:  ``[0xB1, operation, action]``
Program: ``[0xB2, operation, action]``  (same op/action codes as remote)

Mode / queue control (``operation=0xFF``):
- enter program mode: ``b2 ff ff``
- enter remote mode:  ``b2 ff fe``
- play program queue: ``b2 ff f1``
- clear program queue: ``b2 ff f2``
"""

from __future__ import annotations

from gadgetpanda.dog.actions import Action, Move

UUID_SERVICE = "0000ffe5-0000-1000-8000-00805f9b34fb"
UUID_NOTIFY = "0000ffe8-0000-1000-8000-00805f9b34fb"
UUID_WRITE = "0000ffe9-0000-1000-8000-00805f9b34fb"

PREFIX_REMOTE = 0xB1
PREFIX_PROGRAM = 0xB2

# Official remote hold-to-move repeat interval (seconds)
HOLD_INTERVAL_S = 0.05

DEFAULT_NAME_FILTERS: tuple[str, ...] = (
    "FY",
    "X1",
    "JC",
    "DOG",
    "ROBOT",
    "XHY",
    "小智狗",
    "新鸿洋",
    "智狗",
)

CONTROL_CODES: dict[Action | Move, tuple[int, int]] = {
    Move.FORWARD: (1, 0),
    Move.BACKWARD: (2, 0),
    Move.TURN_LEFT: (3, 0),
    Move.TURN_RIGHT: (4, 0),
    Move.STOP: (5, 0),
    Action.GREET: (0, 1),
    Action.BLESS: (0, 2),
    Action.KUNG_FU: (0, 3),
    Action.PEE: (0, 4),
    Action.TURN_OVER: (0, 5),
    Action.DANCE: (0, 6),
    Action.LEARN: (0, 7),
    Action.SONG: (0, 8),
    Action.SIT_DOWN: (0, 9),
    Action.ACT_CUTE: (0, 10),
    Action.LIE_DOWN: (0, 11),
    Action.VOICE: (0, 12),
    Action.HAND_SHAKE: (0, 13),
    Action.JUMP: (0, 14),
    Action.PUSH_UPS: (0, 15),
    Action.HAND_STAND: (0, 16),
    Action.SWIM: (0, 17),
}

PROGRAM_VERBS: frozenset[Action | Move] = frozenset(
    {
        Move.FORWARD,
        Move.BACKWARD,
        Move.TURN_LEFT,
        Move.TURN_RIGHT,
        Action.GREET,
        Action.BLESS,
        Action.PEE,
        Action.KUNG_FU,
        Action.TURN_OVER,
        Action.SIT_DOWN,
        Action.ACT_CUTE,
        Action.LIE_DOWN,
        Action.PUSH_UPS,
        Action.HAND_STAND,
        Action.SWIM,
        Action.DANCE,
        Action.HAND_SHAKE,
        Action.JUMP,
    }
)

PROGRAM_ENTER = bytes((PREFIX_PROGRAM, 0xFF, 0xFF))
PROGRAM_EXIT_TO_REMOTE = bytes((PREFIX_PROGRAM, 0xFF, 0xFE))
PROGRAM_PLAY = bytes((PREFIX_PROGRAM, 0xFF, 0xF1))
PROGRAM_CLEAR = bytes((PREFIX_PROGRAM, 0xFF, 0xF2))


def looks_like_dog(name: str | None, filters: tuple[str, ...] = DEFAULT_NAME_FILTERS) -> bool:
    if not name:
        return False
    upper = name.upper()
    return any(token.upper() in upper for token in filters)


def parse_hex_payload(text: str) -> bytes:
    """Accept 'aa bb 01' or 'aabb01' hex dumps."""
    cleaned = "".join(ch for ch in text.strip() if ch not in " \t\n\r:-")
    if len(cleaned) % 2:
        raise ValueError(f"odd-length hex payload: {text!r}")
    return bytes.fromhex(cleaned)


def frame(prefix: int, operation: int, action: int = 0) -> bytes:
    return bytes((prefix & 0xFF, operation & 0xFF, action & 0xFF))


def remote_frame(operation: int, action: int = 0) -> bytes:
    return frame(PREFIX_REMOTE, operation, action)


def program_frame(operation: int, action: int = 0) -> bytes:
    return frame(PREFIX_PROGRAM, operation, action)


def codes_for(verb: Action | Move) -> tuple[int, int]:
    try:
        return CONTROL_CODES[verb]
    except KeyError as exc:
        raise KeyError(f"no control code for {verb!r}") from exc


def remote_opcodes() -> dict[Action | Move, bytes]:
    return {verb: remote_frame(op, act) for verb, (op, act) in CONTROL_CODES.items()}


def program_opcodes() -> dict[Action | Move, bytes]:
    return {
        verb: program_frame(op, act)
        for verb, (op, act) in CONTROL_CODES.items()
        if verb in PROGRAM_VERBS
    }


def is_scan_marker(payload: bytes) -> bool:
    """True if an advertisement blob starts with ``a1 b1``."""
    return len(payload) >= 2 and payload[0] == 0xA1 and payload[1] == 0xB1
