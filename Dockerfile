# Gadget Panda host runtime (Linux). BLE + Wi‑Fi need host networking / D-Bus.
# See docs/docker.md — macOS Docker Desktop cannot passthrough radio hardware.

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Soft license store inside the container (mount a volume to persist)
    HOME=/root

RUN apt-get update && apt-get install -y --no-install-recommends \
      bluez \
      bluez-tools \
      dbus \
      libdbus-1-3 \
      libglib2.0-0 \
      network-manager \
      wireless-tools \
      iw \
      iproute2 \
      rfkill \
      ca-certificates \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples
COPY docs ./docs

RUN pip install --no-cache-dir ".[ui,mqtt]"

# Persist license seed / token across runs when a volume is mounted here
VOLUME ["/root/.gadgetpanda"]

ENTRYPOINT ["gadgetpanda"]
CMD ["--help"]
