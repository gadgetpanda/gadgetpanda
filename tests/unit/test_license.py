"""Soft license unit tests (honor-system entitlements)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from nacl.signing import SigningKey

from gadgetpanda.license.client import FeatureDenied, License, init, require
from gadgetpanda.license.crypto import sign_token, verify_token
from gadgetpanda.license.features import FEATURE_IDS, PRESETS, validate_features
from gadgetpanda.license.store import LicenseStore, device_fingerprint

# Ephemeral keypair for tests only — never ship a production private key.
_SK = SigningKey.generate()
PRIV = _SK.encode().hex()
PUB = _SK.verify_key.encode().hex()


def test_feature_catalog_covers_presets():
    for name, ids in PRESETS.items():
        assert ids <= FEATURE_IDS, name
    validate_features(["ring.scan", "drone.ui"])


def test_sign_verify_roundtrip():
    payload = {
        "device_id": "abc",
        "exp": int(time.time()) + 3600,
        "features": ["ring.scan", "dog.connect"],
        "iat": int(time.time()),
        "kid": "k1",
    }
    token = sign_token(payload, PRIV)
    out = verify_token(token, PUB)
    assert out["kid"] == "k1"
    assert out["features"] == ["ring.scan", "dog.connect"]


def test_soft_open_without_key(monkeypatch):
    monkeypatch.delenv("GADGETPANDA_LICENSE_KEY", raising=False)
    monkeypatch.delenv("GADGETPANDA_LICENSE_REQUIRED", raising=False)
    monkeypatch.delenv("GADGETPANDA_LICENSE_BYPASS", raising=False)
    lic = License()
    lic.require("ring.scan")  # open


def test_required_mode_denies(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GADGETPANDA_LICENSE_REQUIRED", "1")
    monkeypatch.delenv("GADGETPANDA_LICENSE_BYPASS", raising=False)
    store = LicenseStore(tmp_path / "license.json")
    lic = License(_store=store)
    with pytest.raises(FeatureDenied):
        lic.require("ring.scan")


def test_bypass(monkeypatch):
    monkeypatch.setenv("GADGETPANDA_LICENSE_BYPASS", "1")
    lic = init(bypass=True)
    require("drone.rtsp")


def test_offline_cached_token(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GADGETPANDA_LICENSE_BYPASS", raising=False)
    monkeypatch.setenv("GADGETPANDA_LICENSE_REQUIRED", "1")
    store = LicenseStore(tmp_path / "license.json")
    device = device_fingerprint()
    payload = {
        "device_id": device,
        "exp": int(time.time()) + 86400,
        "features": ["ring.scan", "ring.connect"],
        "iat": int(time.time()),
        "kid": "offline",
    }
    token = sign_token(payload, PRIV)
    record = store.ensure_seed("gp_live_test", "https://example.test")
    record.token = token
    record.token_payload = payload
    store.save(record)

    lic = License(api_key="gp_live_test", _store=store)
    # verify_token uses embedded DEFAULT public key — override via monkeypatch
    monkeypatch.setattr(
        "gadgetpanda.license.client.verify_token",
        lambda tok, public_key=None: verify_token(tok, PUB),
    )
    status = lic.load_cached()
    assert status is not None
    assert "ring.scan" in lic.features
    lic.require("ring.scan")
    with pytest.raises(FeatureDenied):
        lic.require("drone.ui")


def test_cli_license_features(capsys):
    from gadgetpanda.cli import main

    main(["license", "features"])
    out = capsys.readouterr().out
    assert "ring.scan" in out
    assert "drone.rtsp" in out
