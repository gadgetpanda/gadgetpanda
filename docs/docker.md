# Docker (BLE + Wi‑Fi)

Image packages `gadgetpanda` with BlueZ clients, `nmcli`, and ffmpeg so you can scan rings/dogs and join drone APs **from a Linux host**.

## Reality check

| Host | BLE | Wi‑Fi join (`drone wifi`) |
|------|-----|---------------------------|
| Linux / Raspberry Pi | Yes — via host BlueZ D-Bus | Yes — via host NetworkManager |
| macOS Docker Desktop | No | No |
| Windows Docker Desktop | No (use WSL2 + BlueZ only if you know the stack) | No |

On Mac/Windows, install Python on the host. Docker is for Linux gateways/lab PCs.

## Quick start (Linux)

```bash
cd gadgetpanda
chmod +x scripts/docker-run.sh
./scripts/docker-run.sh ring scan
./scripts/docker-run.sh dog scan
./scripts/docker-run.sh drone wifi status
./scripts/docker-run.sh ring ui --demo --host 0.0.0.0 --port 8765
```

Or with Compose directly:

```bash
docker compose build
docker compose run --rm panda ring scan
docker compose run --rm panda drone wifi join FLOW-UFO-xxxx
```

## What gets passed in

`docker-compose.yml` uses:

- `network_mode: host` — same L2/L3 as the host (drone `192.168.1.1`, UI ports)
- `privileged: true` + `/dev/rfkill` + `/dev/bus/usb` — HCI / USB radios
- `/var/run/dbus` + `/run/dbus` — host BlueZ + NetworkManager
- `$HOME/.gadgetpanda` — soft-license seed stays on the host

UI ports (`8765` / `8766` / `8767`) are reachable on the host IP because of host networking.

## License inside the container

```bash
docker compose run --rm panda license activate gp_live_…
docker compose run --rm panda license status
```

Device fingerprint uses container hostname/MAC; keep the volume mount so the seed does not rotate every rebuild.

## Troubleshooting

- **No adapters / scan empty** — Bluetooth enabled on host? `bluetoothctl show` on the host should work first.
- **`nmcli` fails** — install/enable NetworkManager on the **host**; the container only drives it over D-Bus.
- **Permission denied on USB** — confirm the compose `devices:` paths exist (`ls /dev/bus/usb`).
