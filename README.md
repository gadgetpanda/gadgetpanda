# Gadget Panda

**One Python host. Three toys. Infinite maker projects.**

`IDEA → CODE → PROTOTYPE → COMMUNITY`

Open-source runtime for makers who want **raw sensors and real control** — not a locked wellness app.

| Device | Link | What you get |
|---|---|---|
| **RING503PANDA** | Bluetooth LE | PPG · IMU · HR/HRV · temp · SpO₂ · sport/health · battery |
| **SoftDog (X1)** | Bluetooth LE | Actions · move/hold · program queue · web remote |
| **FLOW-UFO** | Wi‑Fi UDP + RTSP | Stick loop · takeoff/land · FPV remote · Wi‑Fi join helpers |

Runs on **Mac · Linux · Windows · Raspberry Pi**.

```bash
pip install 'gadgetpanda[ui]'
gadgetpanda ring ui --demo    # http://127.0.0.1:8765
gadgetpanda dog ui --demo     # http://127.0.0.1:8766
gadgetpanda drone ui --demo   # http://127.0.0.1:8767
```

---

## Why Gadget Panda

- **Host-side Python** — scan, connect, stream, command from your laptop or Pi
- **Realtime UIs** included (Tesla-inspired black / red / gold) when you install `[ui]`
- **Fine-grained APIs** — event callbacks, CLI shells, MQTT bridge (optional)
- **MIT** — fork it, ship it, teach with it

---

## Ring — wear it, stream it

Heart rate, PPG waveform, 6-axis IMU, temperature, SpO₂, sport/health packs.

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

Dashboard modes: all · BLE HR · PPG+HR · vitals · motion · activity  
Docs: [docs/concept.md](docs/concept.md) · [docs/protocol.md](docs/protocol.md)

---

## SoftDog — play, program, remote

BLE fun dog (X1 profile): sit, jump, voice FX, directional hold, program sequences.

```bash
gadgetpanda dog scan
gadgetpanda dog connect <addr> --shell
gadgetpanda dog action <addr> sit_down
gadgetpanda dog move <addr> forward
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

Docs: [docs/dog/concept.md](docs/dog/concept.md) · [docs/dog/protocol.md](docs/dog/protocol.md)

---

## FLOW-UFO — stick, fly, see

Wi‑Fi mini drone (GL stick frames): 50 ms stick loop, heartbeat, takeoff/land, RTSP preview.

```bash
# Join the craft hotspot first (Mac/Linux helpers included)
gadgetpanda drone wifi join "FLOW-UFO-xxxx"
gadgetpanda drone wifi status
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

FPV remote at `http://127.0.0.1:8767` (needs craft Wi‑Fi + `ffmpeg` via `[ui]`).  
Docs: [docs/drone/concept.md](docs/drone/concept.md) · [docs/drone/protocol.md](docs/drone/protocol.md)

---

## Install

```bash
pip install gadgetpanda           # core (BLE + drone protocol)
pip install 'gadgetpanda[ui]'     # dashboards + FPV (FastAPI, ffmpeg)
pip install 'gadgetpanda[mqtt]'   # MQTT bridge
```

From source:

```bash
git clone <repo> && cd gadgetpanda
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[ui,dev]"
```

**Needs:** Python 3.11+ · real BLE/Wi‑Fi hardware (no radio in emulators)  
**Docker (Linux):** host network + BlueZ/NetworkManager — see [docs/docker.md](docs/docker.md)

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

Honor-system feature keys (30-day, one device). Soft by default — no key means open.  
See [docs/license.md](docs/license.md).

```bash
gadgetpanda license features
gadgetpanda license activate gp_live_…
gadgetpanda license status
```

---

## License

**MIT** — host Python in `src/gadgetpanda/`, examples, tests, and maker docs.
