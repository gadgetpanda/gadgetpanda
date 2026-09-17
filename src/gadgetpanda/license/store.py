"""Local license store + device fingerprint (soft binding)."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import secrets
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


def default_store_path() -> Path:
    override = os.environ.get("GADGETPANDA_LICENSE_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".gadgetpanda" / "license.json"


def device_fingerprint() -> str:
    """Stable-ish host id for soft device binding (not a hardware TPM claim)."""
    parts = [
        platform.node(),
        platform.system(),
        platform.machine(),
        str(uuid.getnode()),  # primary MAC as int
        os.environ.get("GADGETPANDA_DEVICE_SALT", ""),
    ]
    raw = "|".join(parts).encode()
    return hashlib.sha256(raw).hexdigest()[:32]


@dataclass
class LicenseRecord:
    api_key: str
    seed: str
    device_id: str
    token: str | None = None
    token_payload: dict | None = None
    server_url: str | None = None

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict) -> LicenseRecord:
        return cls(
            api_key=str(data["api_key"]),
            seed=str(data["seed"]),
            device_id=str(data["device_id"]),
            token=data.get("token"),
            token_payload=data.get("token_payload"),
            server_url=data.get("server_url"),
        )


class LicenseStore:
    def __init__(self, path: Path | None = None):
        self.path = path or default_store_path()

    def load(self) -> LicenseRecord | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return LicenseRecord.from_json(data)

    def save(self, record: LicenseRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(record.to_json(), indent=2) + "\n", encoding="utf-8")
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def ensure_seed(self, api_key: str, server_url: str | None = None) -> LicenseRecord:
        existing = self.load()
        device_id = device_fingerprint()
        if existing and existing.api_key == api_key and existing.device_id == device_id:
            if server_url and not existing.server_url:
                existing.server_url = server_url
                self.save(existing)
            return existing
        if existing and existing.api_key == api_key and existing.device_id != device_id:
            raise RuntimeError(
                "license seed is bound to another device — logout on the original machine first"
            )
        record = LicenseRecord(
            api_key=api_key,
            seed=secrets.token_hex(32),
            device_id=device_id,
            server_url=server_url,
        )
        self.save(record)
        return record
