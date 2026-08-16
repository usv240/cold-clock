"""Firestore clock and wake adapters with transactional exactly-once claims."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from spine.clock import ClockState, ClockStateStore
from spine.wake import Wake, WakeStatus, WakeStore


def _as_utc(value: Any) -> Any:
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _wake_to_doc(wake: Wake) -> dict[str, Any]:
    doc = asdict(wake)
    doc["status"] = wake.status.value
    doc.pop("wake_id")
    return doc


def _doc_to_wake(wake_id: str, raw: dict[str, Any]) -> Wake:
    doc = {key: _as_utc(value) for key, value in raw.items()}
    return Wake(
        wake_id=wake_id,
        run_id=doc["run_id"],
        kind=doc["kind"],
        due_at=doc["due_at"],
        status=WakeStatus(doc["status"]),
        attempts=int(doc.get("attempts", 0)),
        lease_token=doc.get("lease_token"),
        lease_expires_at=doc.get("lease_expires_at"),
        payload=doc.get("payload") or {},
        cancelled_reason=doc.get("cancelled_reason"),
        last_error=doc.get("last_error"),
    )


class FirestoreClockStateStore(ClockStateStore):
    def __init__(self, client: firestore.Client, namespace: str) -> None:
        safe = namespace.strip().lower()
        if not safe or not safe.replace("-", "").replace("_", "").isalnum():
            raise ValueError("clock namespace contains unsupported characters")
        self._ref = client.collection("sim").document(f"clock-{safe}")

    def read(self) -> ClockState:
        snapshot = self._ref.get()
        if not snapshot.exists:
            return ClockState()
        data = snapshot.to_dict() or {}
        return ClockState(
            offset_seconds=float(data.get("offset_seconds", 0.0)),
            frozen_at=_as_utc(data.get("frozen_at")),
        )

    def write(self, state: ClockState) -> None:
        self._ref.set(
            {"offset_seconds": state.offset_seconds, "frozen_at": state.frozen_at},
            merge=False,
        )


class FirestoreWakeStore(WakeStore):
    def __init__(self, client: firestore.Client, collection: str) -> None:
        self._client = client
        self._wakes = client.collection(collection)

    def put_if_absent(self, wake: Wake) -> Wake:
        ref = self._wakes.document(wake.wake_id)
        transaction = self._client.transaction()

        @firestore.transactional
        def create(txn):
            snapshot = ref.get(transaction=txn)
            if snapshot.exists:
                return _doc_to_wake(wake.wake_id, snapshot.to_dict() or {})
            txn.set(ref, _wake_to_doc(wake))
            return wake

        return create(transaction)

    def get(self, wake_id: str) -> Wake | None:
        snapshot = self._wakes.document(wake_id).get()
        return _doc_to_wake(wake_id, snapshot.to_dict() or {}) if snapshot.exists else None

    def put(self, wake: Wake) -> None:
        self._wakes.document(wake.wake_id).set(_wake_to_doc(wake))

    def due(self, now: datetime, limit: int) -> list[Wake]:
        pending = (
            self._wakes.where(filter=firestore.FieldFilter("due_at", "<=", now))
            .where(filter=firestore.FieldFilter("status", "==", WakeStatus.PENDING.value))
            .limit(limit)
            .stream()
        )
        stale = (
            self._wakes.where(filter=firestore.FieldFilter("lease_expires_at", "<=", now))
            .where(filter=firestore.FieldFilter("status", "==", WakeStatus.CLAIMED.value))
            .limit(limit)
            .stream()
        )
        rows = [_doc_to_wake(item.id, item.to_dict() or {}) for item in pending]
        rows.extend(_doc_to_wake(item.id, item.to_dict() or {}) for item in stale)
        unique = {row.wake_id: row for row in rows if row.due_at <= now}
        return sorted(unique.values(), key=lambda row: row.due_at)[:limit]

    def try_claim(self, wake_id: str, token: str, now: datetime, expires: datetime) -> Wake | None:
        ref = self._wakes.document(wake_id)
        transaction = self._client.transaction()

        @firestore.transactional
        def claim(txn):
            snapshot = ref.get(transaction=txn)
            if not snapshot.exists:
                return None
            wake = _doc_to_wake(wake_id, snapshot.to_dict() or {})
            claimable = wake.status is WakeStatus.PENDING or (
                wake.status is WakeStatus.CLAIMED
                and wake.lease_expires_at is not None
                and wake.lease_expires_at <= now
            )
            if wake.due_at > now or not claimable:
                return None
            claimed = replace(
                wake,
                status=WakeStatus.CLAIMED,
                attempts=wake.attempts + 1,
                lease_token=token,
                lease_expires_at=expires,
            )
            txn.set(ref, _wake_to_doc(claimed))
            return claimed

        return claim(transaction)

    def for_run(self, run_id: str) -> list[Wake]:
        rows = self._wakes.where(filter=firestore.FieldFilter("run_id", "==", run_id)).stream()
        return sorted(
            (_doc_to_wake(item.id, item.to_dict() or {}) for item in rows),
            key=lambda row: row.due_at,
        )

