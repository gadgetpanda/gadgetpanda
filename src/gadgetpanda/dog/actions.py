"""High-level verbs for fun-dog remote / program control."""

from __future__ import annotations

from enum import Enum

from gadgetpanda.dog.capabilities import Capability


class Move(Enum):
    """Directional motion (remote hold / single write)."""

    FORWARD = "forward"
    BACKWARD = "backward"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    STOP = "stop"


class Action(Enum):
    """Discrete poses / social / onboard sound effects."""

    SIT_DOWN = "sit_down"
    LIE_DOWN = "lie_down"
    HAND_STAND = "hand_stand"
    JUMP = "jump"
    TURN_OVER = "turn_over"
    DANCE = "dance"
    SWIM = "swim"
    PUSH_UPS = "push_ups"
    KUNG_FU = "kung_fu"
    GREET = "greet"
    HAND_SHAKE = "hand_shake"
    ACT_CUTE = "act_cute"
    BLESS = "bless"
    PEE = "pee"
    LEARN = "learn"
    SONG = "song"
    VOICE = "voice"


MOVE_CAPABILITY: dict[Move, Capability] = {
    Move.FORWARD: Capability.MOVE_BASIC,
    Move.BACKWARD: Capability.MOVE_BASIC,
    Move.TURN_LEFT: Capability.MOVE_BASIC,
    Move.TURN_RIGHT: Capability.MOVE_BASIC,
    Move.STOP: Capability.MOVE_BASIC,
}

ACTION_CAPABILITY: dict[Action, Capability] = {
    Action.SIT_DOWN: Capability.POSE_SIT,
    Action.LIE_DOWN: Capability.POSE_LIE,
    Action.HAND_STAND: Capability.POSE_HANDSTAND,
    Action.JUMP: Capability.POSE_JUMP,
    Action.TURN_OVER: Capability.POSE_ROLL,
    Action.DANCE: Capability.POSE_DANCE,
    Action.SWIM: Capability.POSE_SWIM,
    Action.PUSH_UPS: Capability.POSE_PUSH_UPS,
    Action.KUNG_FU: Capability.POSE_KUNG_FU,
    Action.GREET: Capability.SOCIAL_GREET,
    Action.HAND_SHAKE: Capability.SOCIAL_HANDSHAKE,
    Action.ACT_CUTE: Capability.SOCIAL_ACT_CUTE,
    Action.BLESS: Capability.SOCIAL_BLESS,
    Action.PEE: Capability.SOCIAL_PEE,
    Action.LEARN: Capability.SOCIAL_LEARN,
    Action.SONG: Capability.FX_SOUND,
    Action.VOICE: Capability.FX_VOICE,
}
