"""Durable follow-up registration for every path that advances a case.

Wakes are registered idempotently by (case, kind), so re-running registration after a crash or a
retried request cannot create a second wake. Registration is the only place the workflow decides
what the background worker should do later; the worker itself lives in ``wake_actions``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

REVIEW_FOLLOWUP_MINUTES = 30
RECEIPT_FOLLOWUP_MINUTES = 60


def _record(case: dict[str, Any], wake) -> None:
    rows = case.setdefault("scheduled_wakes", [])
    if not any(row["wake_id"] == wake.wake_id for row in rows):
        rows.append({"wake_id": wake.wake_id, "kind": wake.kind, "due_at": wake.due_at.isoformat()})


def register_followups(case: dict[str, Any], scheduler) -> list[str]:
    """Register the wakes appropriate to the case's current state. Returns the kinds registered."""
    if scheduler is None:
        return []
    case_id = case["case_id"]
    registered: list[str] = []
    if case["status"] == "awaiting_professional_review":
        _record(case, scheduler.sleep_for(case_id, "review_followup", timedelta(minutes=REVIEW_FOLLOWUP_MINUTES)))
        registered.append("review_followup")
    elif (case.get("review") or {}).get("decision"):
        cancelled = scheduler.cancel_kind(case_id, "review_followup", "qualified disposition recorded")
        if cancelled:
            case.setdefault("cancelled_wakes", []).extend(cancelled)
    if case["status"] == "delivery_dispatched":
        eta = int((case.get("delivery") or {}).get("eta_minutes") or 0)
        _record(case, scheduler.sleep_for(case_id, "courier_status_poll", timedelta(minutes=max(eta, 0))  # an ETA of 0 means the next scheduler scan polls the courier))
        registered.append("courier_status_poll")
        _record(case, scheduler.sleep_for(case_id, "receipt_followup", timedelta(minutes=RECEIPT_FOLLOWUP_MINUTES)))
        registered.append("receipt_followup")
    return registered
