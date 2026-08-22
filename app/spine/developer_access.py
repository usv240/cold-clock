"""Self-service developer keys with privacy-preserving daily quotas.

The public key is returned once. Only an HMAC digest and a keyed network
fingerprint are persisted. Firestore transactions make quota checks atomic.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
import threading
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field


DAILY_REQUEST_LIMIT = 50
DAILY_KEY_ISSUANCE_LIMIT = 5
KEY_LIFETIME_DAYS = 180


class AccessError(Exception):
    pass


class IssuanceLimitExceeded(AccessError):
    pass


class InvalidAPIKey(AccessError):
    pass


class DailyQuotaExceeded(AccessError):
    def __init__(self, reset_at: str) -> None:
        super().__init__("daily API quota exhausted")
        self.reset_at = reset_at


class AccessStore(Protocol):
    def issue(self, issue_id: str, key_id: str, key_record: dict[str, Any], issue_record: dict[str, Any]) -> None: ...
    def consume(self, key_id: str, key_digest: str, key_usage_id: str, network_usage_id: str, now: datetime, reset_at: str, limit: int) -> int: ...


class MemoryAccessStore:
    def __init__(self) -> None:
        self.keys: dict[str, dict[str, Any]] = {}
        self.issues: dict[str, dict[str, Any]] = {}
        self.usage: dict[str, int] = {}
        self._lock = threading.Lock()

    def issue(self, issue_id: str, key_id: str, key_record: dict[str, Any], issue_record: dict[str, Any]) -> None:
        with self._lock:
            count = int(self.issues.get(issue_id, {}).get("count", 0))
            if count >= DAILY_KEY_ISSUANCE_LIMIT:
                raise IssuanceLimitExceeded("five self-service keys may be issued per network per UTC day")
            self.keys[key_id] = deepcopy(key_record)
            self.issues[issue_id] = {**deepcopy(issue_record), "count": count + 1}

    def consume(self, key_id: str, key_digest: str, key_usage_id: str, network_usage_id: str, now: datetime, reset_at: str, limit: int) -> int:
        with self._lock:
            record = self.keys.get(key_id)
            if not record or record.get("revoked") or not hmac.compare_digest(record.get("key_digest", ""), key_digest):
                raise InvalidAPIKey("invalid API key")
            if now >= datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00")):
                raise InvalidAPIKey("API key expired")
            key_count = self.usage.get(key_usage_id, 0)
            network_count = self.usage.get(network_usage_id, 0)
            if key_count >= limit or network_count >= limit:
                raise DailyQuotaExceeded(reset_at)
            self.usage[key_usage_id] = key_count + 1
            self.usage[network_usage_id] = network_count + 1
            return limit - max(key_count + 1, network_count + 1)


class FirestoreAccessStore:
    def __init__(self, client: Any, namespace: str) -> None:
        self.client = client
        self.keys = client.collection(f"{namespace}_developer_keys")
        self.issues = client.collection(f"{namespace}_developer_issuance")
        self.usage = client.collection(f"{namespace}_developer_usage")

    def issue(self, issue_id: str, key_id: str, key_record: dict[str, Any], issue_record: dict[str, Any]) -> None:
        from google.cloud import firestore

        transaction = self.client.transaction()
        issue_ref = self.issues.document(issue_id)
        key_ref = self.keys.document(key_id)

        @firestore.transactional
        def commit(txn: Any) -> None:
            snapshot = issue_ref.get(transaction=txn)
            count = int((snapshot.to_dict() or {}).get("count", 1)) if snapshot.exists else 0
            if count >= DAILY_KEY_ISSUANCE_LIMIT:
                raise IssuanceLimitExceeded("five self-service keys may be issued per network per UTC day")
            txn.set(key_ref, key_record)
            txn.set(issue_ref, {**issue_record, "count": count + 1})

        commit(transaction)

    def consume(self, key_id: str, key_digest: str, key_usage_id: str, network_usage_id: str, now: datetime, reset_at: str, limit: int) -> int:
        from google.cloud import firestore

        transaction = self.client.transaction()
        key_ref = self.keys.document(key_id)
        key_usage_ref = self.usage.document(key_usage_id)
        network_usage_ref = self.usage.document(network_usage_id)

        @firestore.transactional
        def commit(txn: Any) -> int:
            key_snapshot = key_ref.get(transaction=txn)
            if not key_snapshot.exists:
                raise InvalidAPIKey("invalid API key")
            record = key_snapshot.to_dict()
            if record.get("revoked") or not hmac.compare_digest(record.get("key_digest", ""), key_digest):
                raise InvalidAPIKey("invalid API key")
            if now >= datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00")):
                raise InvalidAPIKey("API key expired")
            key_snapshot_usage = key_usage_ref.get(transaction=txn)
            network_snapshot_usage = network_usage_ref.get(transaction=txn)
            key_count = int((key_snapshot_usage.to_dict() or {}).get("count", 0)) if key_snapshot_usage.exists else 0
            network_count = int((network_snapshot_usage.to_dict() or {}).get("count", 0)) if network_snapshot_usage.exists else 0
            if key_count >= limit or network_count >= limit:
                raise DailyQuotaExceeded(reset_at)
            txn.set(key_usage_ref, {"count": key_count + 1, "reset_at": reset_at})
            txn.set(network_usage_ref, {"count": network_count + 1, "reset_at": reset_at})
            return limit - max(key_count + 1, network_count + 1)

        return commit(transaction)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _next_utc_day(now: datetime) -> datetime:
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def client_network(request: Request) -> str:
    """Return a best-effort client address; it is never persisted in plaintext."""
    forwarded = request.headers.get("x-forwarded-for", "")
    candidates = [forwarded.rsplit(",", 1)[-1].strip()] if forwarded else []
    if request.client:
        candidates.append(request.client.host)
    for candidate in candidates:
        try:
            return str(ipaddress.ip_address(candidate))
        except (ValueError, TypeError):
            continue
    return "unavailable"


@dataclass
class DeveloperAccessManager:
    store: AccessStore
    namespace: str
    key_prefix: str
    pepper: str
    now: Callable[[], datetime] = _utc_now
    limit: int = DAILY_REQUEST_LIMIT

    def _digest(self, value: str) -> str:
        return hmac.new(self.pepper.encode(), value.encode(), hashlib.sha256).hexdigest()

    def network_fingerprint(self, network: str) -> str:
        return self._digest(f"network:{network}")

    def issue(self, network: str, label: str) -> dict[str, Any]:
        now = self.now().astimezone(timezone.utc)
        day = now.date().isoformat()
        network_fingerprint = self.network_fingerprint(network)
        key_id = secrets.token_hex(6)
        raw_key = f"{self.key_prefix}{key_id}.{secrets.token_urlsafe(32)}"
        expires_at = now + timedelta(days=KEY_LIFETIME_DAYS)
        issue_id = self._digest(f"issue:{day}:{network_fingerprint}")
        self.store.issue(
            issue_id,
            key_id,
            {
                "key_id": key_id,
                "key_digest": self._digest(raw_key),
                "label": label.strip(),
                "created_at": _iso(now),
                "expires_at": _iso(expires_at),
                "revoked": False,
            },
            {"issued_at": _iso(now), "day": day, "network_fingerprint": network_fingerprint},
        )
        return {
            "api_key": raw_key,
            "key_id": key_id,
            "created_at": _iso(now),
            "expires_at": _iso(expires_at),
            "daily_request_limit": self.limit,
            "display_once": True,
        }

    def consume(self, raw_key: str | None, network: str) -> dict[str, Any]:
        if not raw_key or not raw_key.startswith(self.key_prefix) or "." not in raw_key:
            raise InvalidAPIKey("missing or invalid API key")
        key_id = raw_key[len(self.key_prefix):].split(".", 1)[0]
        if len(key_id) != 12:
            raise InvalidAPIKey("invalid API key")
        now = self.now().astimezone(timezone.utc)
        day = now.date().isoformat()
        reset_at = _iso(_next_utc_day(now))
        network_fingerprint = self.network_fingerprint(network)
        remaining = self.store.consume(
            key_id,
            self._digest(raw_key),
            self._digest(f"key-usage:{day}:{key_id}"),
            self._digest(f"network-usage:{day}:{network_fingerprint}"),
            now,
            reset_at,
            self.limit,
        )
        return {"key_id": key_id, "limit": self.limit, "remaining": remaining, "reset_at": reset_at}

    def metadata(self) -> dict[str, Any]:
        return {
            "authentication": "X-API-Key",
            "daily_request_limit": self.limit,
            "quota_scope": "both API key and originating network fingerprint, reset at 00:00 UTC",
            "key_issuance": "up to five self-service keys per network fingerprint per UTC day",
            "key_storage": "public key shown once; only an HMAC digest is persisted",
            "network_privacy": "raw client addresses are never persisted",
            "openapi": "/docs",
        }


class KeyRequest(BaseModel):
    label: str = Field(default="Hackathon evaluator", min_length=2, max_length=80)
    acceptable_use_acknowledgement: bool


def build_access_router(manager: DeveloperAccessManager, product: str, example_endpoint: str) -> APIRouter:
    router = APIRouter(prefix="/api/developer", tags=["developer-access"])

    @router.get("")
    def access_metadata() -> dict[str, Any]:
        return {"product": product, "v1_base": "/v1", "example_endpoint": example_endpoint, **manager.metadata()}

    @router.post("/keys", status_code=201)
    def issue_key(payload: KeyRequest, request: Request, response: Response) -> dict[str, Any]:
        if payload.acceptable_use_acknowledgement is not True:
            raise HTTPException(status_code=422, detail="acceptable-use acknowledgement is required")
        try:
            issued = manager.issue(client_network(request), payload.label)
        except IssuanceLimitExceeded as exc:
            raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "86400"}) from exc
        response.headers["Cache-Control"] = "no-store"
        return issued

    return router


def api_key_guard(manager: DeveloperAccessManager):
    header = APIKeyHeader(name="X-API-Key", auto_error=False, scheme_name="DeveloperAPIKey")

    def require_key(request: Request, response: Response, raw_key: str | None = Depends(header)) -> dict[str, Any]:
        try:
            grant = manager.consume(raw_key, client_network(request))
        except InvalidAPIKey as exc:
            raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "APIKey"}) from exc
        except DailyQuotaExceeded as exc:
            raise HTTPException(
                status_code=429,
                detail=str(exc),
                headers={"X-RateLimit-Limit": str(manager.limit), "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": exc.reset_at, "Retry-After": "86400"},
            ) from exc
        response.headers["X-RateLimit-Limit"] = str(grant["limit"])
        response.headers["X-RateLimit-Remaining"] = str(grant["remaining"])
        response.headers["X-RateLimit-Reset"] = grant["reset_at"]
        return grant

    return require_key
