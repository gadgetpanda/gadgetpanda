<div align="center">

<img src="assets/logo.jpg" alt="Gadget Panda" width="160" />

# Gadget Panda

**One Python host. Three toys. Infinite maker projects.**

`IDEA → CODE → PROTOTYPE → COMMUNITY`

Open-source runtime for makers who want **raw sensors and real control** — not a locked wellness app.

[![PyPI](https://img.shields.io/pypi/v/gadgetpanda?color=111111&label=PyPI&logo=pypi&logoColor=white)](https://pypi.org/project/gadgetpanda/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](LICENSE)
[![Platform](https://img.shields.io/badge/Mac%20%7C%20Linux%20%7C%20Windows%20%7C%20Pi-111111)](https://github.com/gadgetpanda/gadgetpanda)

```bash
pip install 'gadgetpanda[ui]'
```

[Docs](docs/concept.md) · [Protocol](docs/protocol.md) · [PyPI](https://pypi.org/project/gadgetpanda/) · [Issues](https://github.com/gadgetpanda/gadgetpanda/issues)

</div>

---

## Devices

| | Device | Link | You get |
|:--:|:--|:--|:--|
| **1** | **RING503PANDA** | Bluetooth LE | PPG · IMU · HR/HRV · temp · SpO₂ · sport/health · battery |
| **2** | **SoftDog (X1)** | Bluetooth LE | Actions · move/hold · program queue · web remote |
| **3** | **FLOW-UFO** | Wi‑Fi UDP + RTSP | Stick loop · takeoff/land · FPV remote · Wi‑Fi helpers |

<div align="center">

| Ring UI | Dog UI | Drone UI |
|:--:|:--:|:--:|
| `:8765` | `:8766` | `:8767` |

```bash
gadgetpanda ring ui --demo
gadgetpanda dog ui --demo
gadgetpanda drone ui --demo
```

</div>

---

## Why Gadget Panda

- **Host-side Python** — scan, connect, stream, and command from a laptop or Pi
- **Realtime UIs** — included with `[ui]` (black / red / gold)
- **Fine-grained APIs** — callbacks, CLI shells, optional MQTT
- **MIT** — fork it, ship it, teach with it

---

## Quick start — Ring

```python
import asyncio
from gadgetpanda import Ring

async def main():
    ring = await Ring.find()
    ring.on("heart_rate", lambda s: print("HR", s.bpm))
    ring.on("imu", lambda samples: print(samples[0] if samples else ""))
    ring.on("ppg", lambda samples: print("ppg", len(samples)))
    async with ring:
        await ring.set_raw_enabled(True)
        await asyncio.Event().wait()

asyncio.run(main())
```

```bash
gadgetpanda ring scan
gadgetpanda ring live
gadgetpanda ring ppg
gadgetpanda ring ui --mode ppg
```

Modes: `all` · BLE HR · PPG+HR · vitals · motion · activity  
Docs: [concept](docs/concept.md) · [protocol](docs/protocol.md)

---

## SoftDog

```bash
gadgetpanda dog scan
gadgetpanda dog connect <addr> --shell
gadgetpanda dog action <addr> sit_down
gadgetpanda dog ui <addr>          # React remote @ :8766
gadgetpanda dog ui --demo
```

```python
from gadgetpanda.dog import Dog, Action, Move

async with Dog(address) as dog:
    await dog.action(Action.SIT_DOWN)
    await dog.hold_move(Move.FORWARD, seconds=1.0)
    await dog.run_program([Action.JUMP, Move.TURN_LEFT, Action.VOICE])
```

Docs: [dog concept](docs/dog/concept.md) · [dog protocol](docs/dog/protocol.md)

---

## FLOW-UFO

```bash
gadgetpanda drone wifi join "FLOW-UFO-xxxx"
gadgetpanda drone scan
gadgetpanda drone ui --wifi "FLOW-UFO-xxxx" --model flow
gadgetpanda drone ui --demo
```

```python
from gadgetpanda.drone import Drone

async with Drone("192.168.1.1", model="flow") as drone:
    await drone.command("takeoff")
    await drone.hold_stick("forward", seconds=1.5)
    await drone.command("land")
```

FPV remote: `http://127.0.0.1:8767` (needs craft Wi‑Fi + `ffmpeg` via `[ui]`)  
Docs: [drone concept](docs/drone/concept.md) · [drone protocol](docs/drone/protocol.md)

---

## Install

```bash
pip install gadgetpanda           # core (BLE + drone protocol)
pip install 'gadgetpanda[ui]'     # dashboards + FPV
pip install 'gadgetpanda[mqtt]'   # MQTT bridge
```

From source:

```bash
git clone https://github.com/gadgetpanda/gadgetpanda.git
cd gadgetpanda
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[ui,dev]"
```

**Needs:** Python 3.11+ · real BLE / Wi‑Fi hardware  
**Docker (Linux):** host network + BlueZ — [docs/docker.md](docs/docker.md)

---

## CLI map

| Namespace | Highlights |
|---|---|
| `gadgetpanda ring …` | `scan` `live` `ppg` `user` `ui` |
| `gadgetpanda dog …` | `scan` `connect` `action` `move` `ui` |
| `gadgetpanda drone …` | `wifi` `scan` `connect` `stick` `cmd` `ui` |
| `gadgetpanda license …` | optional soft entitlements |

---

## Soft license (optional)

Honor-system feature keys. Soft by default — no key means open.  
See [docs/license.md](docs/license.md).

```bash
gadgetpanda license features
gadgetpanda license activate gp_live_…
gadgetpanda license status
```

---

<div align="center">

**MIT** · Small ideas. Bigger possibilities.

[github.com/gadgetpanda](https://github.com/gadgetpanda) · [pypi.org/project/gadgetpanda](https://pypi.org/project/gadgetpanda/)

</div>
