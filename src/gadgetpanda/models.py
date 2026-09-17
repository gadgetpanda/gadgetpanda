from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class AdvertisedRing:
    name: str
    address: str
    rssi: int | None = None

    @property
    def display_name(self) -> str:
        return panda_display_name(self.name, self.address)


def panda_display_name(name: str | None, address: str = "") -> str:
    """Show RING503PANDA-xxxxx / RING503nPANDA-xxxxx."""
    if not name:
        return address or "unknown"
    stripped = brand_display(name.strip())
    upper = stripped.upper()
    if upper.startswith("RING503NPANDA"):
        return f"RING503nPANDA-{_panda_suffix(stripped[len('RING503nPANDA'):], address)}"
    if upper.startswith("RING503PANDA"):
        return f"RING503PANDA-{_panda_suffix(stripped[len('RING503PANDA'):], address)}"
    return stripped


def _panda_suffix(rest: str, address: str) -> str:
    token = "".join(ch for ch in rest if ch.isalnum())
    if token:
        return token.upper()
    hex_addr = "".join(ch for ch in address if ch.isalnum())
    if len(hex_addr) >= 5:
        return hex_addr[-5:].upper()
    return (hex_addr or "00000").upper().zfill(5)


def brand_display(text: str) -> str:
    """Replace manufacturer branding in anything shown to the user."""
    # OEM DIS vendor string (stored as hex so the mark is not littered in source).
    oem = bytes.fromhex("6368696c656166").decode("ascii")
    text = re.sub(re.escape(oem), "gadgetpanda", text, flags=re.IGNORECASE)
    text = re.sub(r"RL503N", "RING503nPANDA", text, flags=re.IGNORECASE)
    text = re.sub(r"RL503", "RING503PANDA", text, flags=re.IGNORECASE)
    return text


def oem_vendor_mark() -> str:
    """Raw OEM manufacturer string as seen on Device Information Service."""
    return bytes.fromhex("6368696c656166").decode("ascii")


def brand_display_value(value):
    if isinstance(value, str):
        return brand_display(value)
    if isinstance(value, dict):
        return {key: brand_display_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(brand_display_value(item) for item in value)
    return value



@dataclass(frozen=True)
class HeartRate:
    bpm: int
    contact: bool | None = None
    rr_intervals: tuple[int, ...] = ()
    energy_kj: int | None = None
    source: str = "ble"


@dataclass(frozen=True)
class Hrv:
    """Host-side SDNN from BLE RR intervals (1/1024 s)."""

    sdnn: float
    sdnn_ms: float
    samples: int


def calculate_hrv(rr_intervals: list[int] | tuple[int, ...]) -> float:
    """Sample standard deviation of RR values in the 500–1200 window."""
    cache = [item for item in rr_intervals if 500 <= item <= 1200]
    if len(cache) < 2:
        return 0.0
    average = sum(cache) / len(cache)
    variance = sum((item - average) ** 2 for item in cache) / (len(cache) - 1)
    return variance**0.5


class HrvTracker:
    """Match the Android SDK: 30 HR packets with RR, then SDNN of the last 29."""

    RR_PACKETS = 30
    NONE_LIMIT = 60

    def __init__(self) -> None:
        self._rr: list[int] = []
        self._packets = 0
        self._none = 0

    def feed(self, rr_intervals: tuple[int, ...] | list[int]) -> Hrv | None:
        if rr_intervals:
            self._none = 0
            self._packets += 1
            self._rr.extend(int(item) for item in rr_intervals)
            if len(self._rr) > 120:
                self._rr = self._rr[-60:]
            if self._packets >= self.RR_PACKETS and len(self._rr) >= 30:
                window = self._rr[-30:-1]
                sdnn = calculate_hrv(window)
                return Hrv(sdnn=sdnn, sdnn_ms=sdnn * 1000.0 / 1024.0, samples=len(window))
            return None
        self._packets = 0
        self._none += 1
        if self._none > self.NONE_LIMIT:
            self._rr.clear()
            return Hrv(sdnn=0.0, sdnn_ms=0.0, samples=0)
        return None

    def reset(self) -> None:
        self._rr.clear()
        self._packets = 0
        self._none = 0


class PpgHrTracker:
    """Estimate BPM from realtime PPG when the ring does not notify 2A37."""

    WINDOW_S = 8.0
    MIN_BPM = 42
    MAX_BPM = 180
    MIN_PEAKS = 3

    def __init__(self) -> None:
        self._times: list[float] = []
        self._values: list[float] = []
        self._prev_t: float | None = None
        self._last_bpm: int | None = None

    def feed(self, samples: list[int] | tuple[int, ...], now: float) -> HeartRate | None:
        channel = _ppg_channel(samples)
        if not channel:
            return None
        if self._prev_t is None:
            self._prev_t = now
            return None
        elapsed = max(now - self._prev_t, 1e-3)
        self._prev_t = now
        step = elapsed / len(channel)
        start = now - elapsed + step
        for index, value in enumerate(channel):
            self._times.append(start + index * step)
            self._values.append(float(value))
        cutoff = now - self.WINDOW_S
        while self._times and self._times[0] < cutoff:
            self._times.pop(0)
            self._values.pop(0)
        if len(self._values) < 24:
            return None
        bpm = _ppg_bpm(self._times, self._values)
        if bpm is None:
            return None
        if self._last_bpm is not None:
            bpm = int(round(self._last_bpm * 0.4 + bpm * 0.6))
        self._last_bpm = bpm
        return HeartRate(bpm=bpm, source="ppg")

    def reset(self) -> None:
        self._times.clear()
        self._values.clear()
        self._prev_t = None
        self._last_bpm = None


def _ppg_channel(samples: list[int] | tuple[int, ...]) -> list[int]:
    values = [int(item) for item in samples]
    if len(values) < 4:
        return values
    even = values[0::2]
    odd = values[1::2]
    if abs(_mean(even) - _mean(odd)) < 0.08 * max(_mean(even), _mean(odd), 1):
        return values
    return even if _spread(even) >= _spread(odd) else odd


def _mean(values: list[int] | list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _spread(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0
    average = _mean(values)
    return sum((item - average) ** 2 for item in values) / len(values)


def _smooth(values: list[float], window: int = 5) -> list[float]:
    if len(values) < window:
        return list(values)
    half = window // 2
    out: list[float] = []
    for index in range(len(values)):
        lo = max(0, index - half)
        hi = min(len(values), index + half + 1)
        out.append(sum(values[lo:hi]) / (hi - lo))
    return out


def _ppg_bpm(times: list[float], values: list[float]) -> int | None:
    trend = _smooth(values, 9)
    ac = [value - base for value, base in zip(values, trend)]
    if len(ac) < 8:
        return None
    ranked = sorted(abs(item) for item in ac)
    threshold = ranked[int(len(ranked) * 0.7)] * 0.45
    if threshold <= 0:
        return None
    min_gap = 60.0 / 180.0
    peaks: list[float] = []
    for index in range(1, len(ac) - 1):
        if ac[index] > ac[index - 1] and ac[index] >= ac[index + 1] and ac[index] > threshold:
            if not peaks or times[index] - peaks[-1] >= min_gap:
                peaks.append(times[index])
    if len(peaks) < 3:
        return None
    intervals = [later - earlier for earlier, later in zip(peaks, peaks[1:])]
    intervals = [item for item in intervals if 60.0 / 180.0 <= item <= 60.0 / 42.0]
    if len(intervals) < 2:
        return None
    intervals.sort()
    median = intervals[len(intervals) // 2]
    bpm = int(round(60.0 / median))
    if bpm < 42 or bpm > 180:
        return None
    return bpm


@dataclass(frozen=True)
class Sport:
    steps: int
    distance_m: float
    calories_kcal: float


@dataclass(frozen=True)
class Health:
    vo2max: int
    breath_rate: int
    emotion: int
    stress: int
    stamina: int


@dataclass(frozen=True)
class Temperature:
    ambient_c: float
    wrist_c: float
    body_c: float


@dataclass(frozen=True)
class BloodOxygen:
    enabled: bool
    spo2: int
    on_wrist: bool


@dataclass(frozen=True)
class UserInfo:
    age: int
    sex: int
    weight_kg: int
    height_cm: int
    user_id: int


@dataclass(frozen=True)
class Birthday:
    year: int
    month: int
    day: int


@dataclass(frozen=True)
class Raw6D:
    acc_x: int
    acc_y: int
    acc_z: int
    gyro_x: int
    gyro_y: int
    gyro_z: int

    @property
    def gyro_mag2(self) -> int:
        return self.gyro_x * self.gyro_x + self.gyro_y * self.gyro_y + self.gyro_z * self.gyro_z


@dataclass(frozen=True)
class PpgSample:
    flag: int
    value: int


@dataclass(frozen=True)
class RawFrame:
    frame: int
    stamp: int
    imu: tuple[Raw6D, ...]
    ppg: tuple[PpgSample, ...]


@dataclass(frozen=True)
class SportHistory:
    stamp_ms: int
    steps: int
    calories: int


@dataclass(frozen=True)
class SleepBlock:
    stamp_ms: int
    actions: tuple[int, ...]


@dataclass(frozen=True)
class HealthHistory:
    start: int
    stamp_ms: int
    type: int
    stress: int
    breath_rate: int
    vo2max: int
    emotion: int
    stamina: int
    heart_rate: int
    spo2: int
    temperature_c: float


@dataclass(frozen=True)
class HeartRateHistory:
    stamp_ms: int
    bpm: int
    progress: int = 0
    total: int = 0


Handler = Callable[..., None]


@dataclass
class EventBus:
    _handlers: dict[str, list[Handler]] = field(default_factory=dict)

    def on(self, event: str, handler: Handler) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def emit(self, event: str, *args, **kwargs) -> None:
        self._dispatch(self._handlers.get(event, ()), args, kwargs)
        self._dispatch(self._handlers.get("*", ()), (event, *args), kwargs)

    @staticmethod
    def _dispatch(handlers: list[Handler], args: tuple, kwargs: dict) -> None:
        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except TypeError:
                handler(*args)
