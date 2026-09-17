"""Ed25519 license token helpers (verify on client, sign on server)."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any


# Embedded verify key for the Gadget Panda soft-license issuer.
# Public only — the matching private key must never ship in this package.
DEFAULT_PUBLIC_KEY_B64 = (
    "10db3a6689124ce983ef0c9dcf7643ccb512ece68d2d0f27867c4f6c4675a1f1"
)


class LicenseCryptoError(ValueError):
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def public_key_bytes(public_key: str | bytes | None = None) -> bytes:
    if public_key is None:
        public_key = DEFAULT_PUBLIC_KEY_B64
    if isinstance(public_key, bytes):
        return public_key
    text = public_key.strip()
    if len(text) == 64 and all(c in "0123456789abcdefABCDEF" for c in text):
        return bytes.fromhex(text)
    return _b64url_decode(text)


def canonical_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sign_token(payload: dict[str, Any], private_key_hex: str) -> str:
    from nacl.signing import SigningKey

    key = SigningKey(bytes.fromhex(private_key_hex))
    body = canonical_payload(payload)
    signed = key.sign(body)
    return _b64url_encode(body) + "." + _b64url_encode(signed.signature)


def verify_token(token: str, public_key: str | bytes | None = None) -> dict[str, Any]:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError

    try:
        body_b64, sig_b64 = token.split(".", 1)
    except ValueError as exc:
        raise LicenseCryptoError("malformed token") from exc
    body = _b64url_decode(body_b64)
    signature = _b64url_decode(sig_b64)
    verify_key = VerifyKey(public_key_bytes(public_key))
    try:
        verify_key.verify(body, signature)
    except BadSignatureError as exc:
        raise LicenseCryptoError("invalid token signature") from exc
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise LicenseCryptoError("token payload must be object")
    exp = int(payload.get("exp") or 0)
    if exp and time.time() > exp:
        raise LicenseCryptoError("license expired")
    return payload


def seed_challenge(seed: str, device_id: str, api_key: str) -> str:
    return hashlib.sha256(f"{api_key}:{device_id}:{seed}".encode()).hexdigest()
