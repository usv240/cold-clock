"""Judge-visible record of the last background worker invocations.

Cloud Run keeps this service at one instance, so an in-process record is enough to show "the
scheduler called us N seconds ago with a verified identity" without console access. It is
evidence for humans, not state the workflow depends on; wakes themselves live in Firestore.
"""
from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any

_lock = Lock()
_status: dict[str, Any] = {
    "scans": 0,
    "dispatched_total": 0,
    "last_scan_at": None,
    "last_identity": None,
    "last_dispatched": [],
    "pushes": 0,
    "last_push_at": None,
    "last_push_kind": None,
}


def record_scan(identity: dict[str, Any], dispatched: list[str]) -> None:
    with _lock:
        _status["scans"] += 1
        _status["dispatched_total"] += len(dispatched)
        _status["last_scan_at"] = datetime.now(timezone.utc).isoformat()
        _status["last_identity"] = identity
        _status["last_dispatched"] = list(dispatched)


def record_push(kind: str) -> None:
    with _lock:
        _status["pushes"] += 1
        _status["last_push_at"] = datetime.now(timezone.utc).isoformat()
        _status["last_push_kind"] = kind


def snapshot() -> dict[str, Any]:
    with _lock:
        data = dict(_status)
    now = datetime.now(timezone.utc)
    for key, target in (("last_scan_at", "seconds_since_last_scan"), ("last_push_at", "seconds_since_last_push")):
        if data.get(key):
            data[target] = int((now - datetime.fromisoformat(data[key])).total_seconds())
        else:
            data[target] = None
    data["expected_scan_interval_seconds"] = 60
    data["note"] = "In-process record since this instance started; durable wake state lives in Firestore."
    return data
