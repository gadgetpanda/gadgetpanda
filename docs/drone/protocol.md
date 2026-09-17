# Drone protocol (V66 / KY UFO stack)

Clean-room notes for the open-source host.

## Transport

| | |
|---|---|
| Link | Wi‑Fi STA → drone AP |
| Control | UDP `192.168.1.1:7099` |
| Preview | RTSP `rtsp://192.168.1.1:7070/webcam` (optional, not required for stick) |
| Heartbeat | `01 01` ≈ every 1 s |

## Stick frame (TC / device type 10)

UDP payload:

```text
03 66 RR PP TT YY FF XX 99
```

| Byte | Meaning |
|---|---|
| `03` | UDP wrapper |
| `66` | head |
| `RR` | roll (aileron), center `80` hex / 128 |
| `PP` | pitch (elevator), center 128 |
| `TT` | throttle, center 128 (`01` coerced to `00` in app) |
| `YY` | yaw, center 128 |
| `FF` | flags (bitfield) |
| `XX` | `RR ^ PP ^ TT ^ YY ^ FF` |
| `99` | tail |

### Flag bits (TC)

| bit | value | meaning |
|---|---|---|
| 0 | 1 | takeoff / fast fly pulse |
| 1 | 2 | land / fast drop pulse |
| 2 | 4 | emergency stop |
| 3 | 8 | circle |
| 4 | 16 | headless |
| 5 | 32 | unlock / return |
| 6 | 64 | light |
| 7 | 128 | gyro calibrate |

## Stick frame (GL / longer)

```text
03 66 14 RR PP TT YY F1 F2 00×10 XX 99
```

Used for GL craft (`--model flow`). FLOW-UFO uses this path.

### Flag bytes (GL)

| | bit | meaning |
|---|---|---|
| F1 | 0 (1) | takeoff **or** land pulse |
| F1 | 1 (2) | emergency |
| F1 | 2 (4) | calibrate |
| F1 | 3 (8) | circle |
| F1 | 4 (16) | light |
| F1 | 6 (64) | gesture |
| F2 | 0 (1) | headless |
| F2 | 1 (2) | **fixed height / altitude hold** (FLOW/GL default on) |

Hover with altitude hold: `… 80 80 80 80 00 02 … 02 99`  
Checksum `XX = RR ^ PP ^ TT ^ YY ^ F1 ^ F2`

Profile `--model flow` enables fixed-height by default.

## Other short UDP commands

| bytes | role |
|---|---|
| `01 01` | heartbeat |
| `08 01` | leave control mode |
| `06 01` / `06 02` | camera switch |
| `09 01` / `09 02` | screen flip |

## Host API

```python
from gadgetpanda.drone import Drone

async with Drone("192.168.1.1", model="flow") as drone:
    await drone.command("takeoff")
    await drone.hold_stick("forward", seconds=1.5)
    await drone.command("land")
```
