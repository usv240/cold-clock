"""Verify Cloud Scheduler OIDC calls before dispatching durable wakes.

``SCHEDULER_AUDIENCE`` may list several comma-separated audiences because a Cloud Run service is
reachable at more than one URL (the deterministic ``…-<project-number>.<region>.run.app`` form and
the ``…-<hash>-uc.a.run.app`` form). The token's audience must match one of them exactly.
"""
from __future__ import annotations
import os
from google.auth.transport.requests import Request
from google.oauth2 import id_token


def configured_audiences() -> list[str]:
    return [item.strip().rstrip("/") for item in os.getenv("SCHEDULER_AUDIENCE", "").split(",") if item.strip()]


def verify_scheduler_token(authorization, verifier=None):
    audiences = configured_audiences(); expected = os.getenv("SCHEDULER_SERVICE_ACCOUNT", "").strip()
    if not audiences or not expected:
        if os.getenv("USE_FIRESTORE", "").lower() in {"1", "true", "yes"}: raise ValueError("scheduler identity is not configured")
        return {"mode": "local-test"}
    if not authorization or not authorization.startswith("Bearer "): raise ValueError("missing scheduler bearer token")
    token = authorization[7:]
    verify = verifier or (lambda tok, aud: id_token.verify_oauth2_token(tok, Request(), audience=aud))
    claims = None; last_error: Exception | None = None
    for audience in audiences:
        try:
            claims = verify(token, audience); break
        except Exception as exc:  # noqa: BLE001 - try the next configured audience
            last_error = exc
    if claims is None: raise ValueError(f"scheduler audience rejected: {type(last_error).__name__ if last_error else 'no audience matched'}")
    if claims.get("email") != expected or claims.get("email_verified") is not True: raise ValueError("scheduler identity rejected")
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}: raise ValueError("scheduler issuer rejected")
    return {"mode": "google-oidc", "email": expected}
