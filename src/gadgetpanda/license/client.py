"""Soft license runtime: activate, offline verify, feature checks."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Iterable

from gadgetpanda.license.crypto import (
    LicenseCryptoError,
    seed_challenge,
    verify_token,
)
from gadgetpanda.license.features import FEATURE_IDS, validate_features
from gadgetpanda.license.store import LicenseRecord, LicenseStore, device_fingerprint

DEFAULT_SERVER = os.environ.get(
    "GADGETPANDA_LICENSE_URL",
    "https://lib.gadgetpanda.app",
)

# Cloudflare Browser Integrity Check bans the default ``Python-urllib/…`` UA (Error 1010).
_USER_AGENT = "GadgetPanda/0.1 (+https://github.com/gadgetpanda/gadgetpanda)"


class LicenseError(RuntimeError):
    pass


class FeatureDenied(LicenseError):
    pass


@dataclass
class License:
    """Process-wide soft license session."""

    api_key: str | None = None
    server_url: str = DEFAULT_SERVER
    features: frozenset[str] = field(default_factory=frozenset)
    device_id: str | None = None
    expires_at: int | None = None
    online: bool = False
    bypass: bool = False
    _store: LicenseStore = field(default_factory=LicenseStore)
    _record: LicenseRecord | None = None

    def require(self, feature: str) -> None:
        if self.bypass or os.environ.get("GADGETPANDA_LICENSE_BYPASS") == "1":
            return
        if not self.api_key and os.environ.get("GADGETPANDA_LICENSE_REQUIRED") != "1":
            # Soft default: open until a key is configured or required mode is on.
            return
        if feature not in FEATURE_IDS:
            raise FeatureDenied(f"unknown feature {feature!r}")
        if feature not in self.features:
            raise FeatureDenied(
                f"feature {feature!r} is not enabled on this license — "
                "manage keys at the Gadget Panda portal"
            )

    def allows(self, feature: str) -> bool:
        try:
            self.require(feature)
            return True
        except FeatureDenied:
            return False

    def status(self) -> dict:
        return {
            "configured": bool(self.api_key) or self.bypass,
            "bypass": self.bypass or os.environ.get("GADGETPANDA_LICENSE_BYPASS") == "1",
            "device_id": self.device_id or device_fingerprint(),
            "features": sorted(self.features),
            "expires_at": self.expires_at,
            "online": self.online,
            "server_url": self.server_url,
            "store": str(self._store.path),
        }

    def activate(
        self,
        api_key: str,
        *,
        server_url: str | None = None,
        offline_ok: bool = True,
    ) -> dict:
        self.api_key = api_key.strip()
        if server_url:
            self.server_url = server_url.rstrip("/")
        record = self._store.ensure_seed(self.api_key, self.server_url)
        self._record = record
        self.device_id = record.device_id

        try:
            payload = self._activate_online(record)
            self.online = True
        except Exception as exc:
            if not offline_ok or not record.token:
                raise LicenseError(f"online activate failed: {exc}") from exc
            payload = verify_token(record.token)
            self._assert_device(payload, record)
            self.online = False

        self._apply_payload(payload, record)
        return self.status()

    def refresh(self, *, offline_ok: bool = True) -> dict:
        if not self.api_key:
            raise LicenseError("no license key configured")
        record = self._store.load()
        if record is None:
            return self.activate(self.api_key, offline_ok=offline_ok)
        self._record = record
        try:
            payload = self._activate_online(record)
            self.online = True
        except Exception:
            if not offline_ok or not record.token:
                raise
            payload = verify_token(record.token)
            self._assert_device(payload, record)
            self.online = False
        self._apply_payload(payload, record)
        return self.status()

    def load_cached(self) -> dict | None:
        record = self._store.load()
        if record is None or not record.token:
            return None
        payload = verify_token(record.token)
        self._assert_device(payload, record)
        self.api_key = record.api_key
        self._record = record
        self.device_id = record.device_id
        self.server_url = record.server_url or self.server_url
        self._apply_payload(payload, record)
        self.online = False
        return self.status()

    def logout(self, *, online: bool = True) -> None:
        record = self._store.load()
        if online and record is not None:
            try:
                self._post(
                    "/v1/license/logout",
                    {
                        "api_key": record.api_key,
                        "device_id": record.device_id,
                        "challenge": seed_challenge(record.seed, record.device_id, record.api_key),
                    },
                )
            except Exception:
                pass
        self._store.clear()
        self.api_key = None
        self.features = frozenset()
        self.device_id = None
        self.expires_at = None
        self._record = None
        self.online = False

    def _apply_payload(self, payload: dict, record: LicenseRecord) -> None:
        features = validate_features(payload.get("features") or [])
        self.features = features
        self.expires_at = int(payload.get("exp") or 0) or None
        record.token_payload = payload
        if record.token is None and payload.get("_token"):
            record.token = payload["_token"]
        self._store.save(record)

    def _assert_device(self, payload: dict, record: LicenseRecord) -> None:
        bound = payload.get("device_id")
        if bound and bound != record.device_id:
            raise LicenseError("license token is bound to a different device")
        if record.device_id != device_fingerprint():
            raise LicenseError("local seed does not match this machine — logout elsewhere first")

    def _activate_online(self, record: LicenseRecord) -> dict:
        data = self._post(
            "/v1/license/activate",
            {
                "api_key": record.api_key,
                "device_id": record.device_id,
                "seed": record.seed,
                "challenge": seed_challenge(record.seed, record.device_id, record.api_key),
            },
        )
        token = data.get("token")
        if not token:
            raise LicenseError("server did not return token")
        payload = verify_token(token)
        self._assert_device(payload, record)
        record.token = token
        payload = dict(payload)
        payload["_token"] = token
        return payload

    def _post(self, path: str, body: dict) -> dict:
        url = self.server_url.rstrip("/") + path
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": _USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LicenseError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LicenseError(str(exc.reason)) from exc


_SESSION = License()


def get_license() -> License:
    return _SESSION


def init(
    api_key: str | None = None,
    *,
    server_url: str | None = None,
    offline_ok: bool = True,
    bypass: bool = False,
) -> License:
    """Configure process license. Call once at app start."""
    lic = get_license()
    lic.bypass = bypass or os.environ.get("GADGETPANDA_LICENSE_BYPASS") == "1"
    if lic.bypass:
        lic.features = frozenset(FEATURE_IDS)
        return lic
    key = api_key or os.environ.get("GADGETPANDA_LICENSE_KEY")
    if server_url:
        lic.server_url = server_url.rstrip("/")
    if key:
        lic.activate(key, server_url=lic.server_url, offline_ok=offline_ok)
    else:
        try:
            lic.load_cached()
        except (LicenseError, LicenseCryptoError, ValueError):
            pass
    return lic


def require(*features: str) -> None:
    lic = get_license()
    for feature in features:
        lic.require(feature)


def require_any(features: Iterable[str]) -> None:
    lic = get_license()
    feats = list(features)
    if any(lic.allows(f) for f in feats):
        return
    raise FeatureDenied(f"need one of: {', '.join(feats)}")
