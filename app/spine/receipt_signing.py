"""Tamper-evident autonomy receipts.

The autonomy proof is derived from persisted state, but a JSON document copied into a submission
can be edited. Signing it with an HMAC keyed by the Secret Manager pepper lets anyone holding a
receipt ask the service whether it is authentic, without the service having to trust the caller.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

SIGNATURE_FIELDS = ("signature", "signature_alg", "verify_endpoint")


def canonical(proof: dict[str, Any]) -> bytes:
    body = {key: value for key, value in proof.items() if key not in SIGNATURE_FIELDS}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sign_receipt(proof: dict[str, Any], pepper: str) -> dict[str, Any]:
    digest = hmac.new(pepper.encode("utf-8"), canonical(proof), hashlib.sha256).hexdigest()
    return {**proof, "signature": digest, "signature_alg": "HMAC-SHA256 over canonical JSON, keyed by Secret Manager pepper", "verify_endpoint": "POST /api/receipts/verify"}


def verify_receipt(proof: dict[str, Any], pepper: str) -> bool:
    supplied = str(proof.get("signature") or "")
    if not supplied:
        return False
    expected = hmac.new(pepper.encode("utf-8"), canonical(proof), hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)
