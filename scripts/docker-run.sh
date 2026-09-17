#!/usr/bin/env bash
# Build (once) and run gadgetpanda in Docker with host BLE / Wi‑Fi (Linux).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" == "Darwin" ]]; then
  cat <<'EOF' >&2
macOS Docker Desktop cannot pass Bluetooth LE or host Wi‑Fi into Linux containers.
Use the native install instead:

  pip install -e ".[ui]"
  gadgetpanda ring scan

On a Linux box / Raspberry Pi, re-run this script there.
EOF
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

if [[ ! -d /var/run/dbus && ! -d /run/dbus ]]; then
  echo "warning: no D-Bus socket found — BLE via BlueZ will likely fail" >&2
fi

ARGS=("$@")
if [[ ${#ARGS[@]} -eq 0 ]]; then
  ARGS=(ring scan)
fi

docker compose build
exec docker compose run --rm --service-ports panda "${ARGS[@]}"
