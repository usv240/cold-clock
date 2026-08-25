"""Idempotent ColdClock wake actions executed by the Cloud Scheduler worker.

Three kinds exist:

* ``courier_status_poll`` fires at the sandbox courier ETA, polls the courier, and closes the case
  when the handoff is confirmed. This is the background transition that finishes the workflow
  without anyone at a screen.
* ``review_followup`` surfaces a review that is still unresolved after thirty minutes.
* ``receipt_followup`` surfaces a delivery that is still unconfirmed after sixty minutes.

None of them makes a medication decision or contacts anyone outside the sandbox.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cold_clock.store import CaseStore
from cold_clock.workflow import _append, confirm_delivery
from spine.wake import Wake

ACTOR = "Background wake agent"


def poll_sandbox_courier(case: dict[str, Any]) -> dict[str, Any]:
    """The sandbox courier connector. It reports ``delivered`` once the ETA has passed."""
    delivery = case.get("delivery") or {}
    if delivery.get("status") != "dispatched":
        return {"status": "not_in_transit", "sandbox": True}
    return {"status": "delivered", "sandbox": True, "delivery_id": delivery.get("delivery_id"), "accessible_handoff": True}


class ColdClockWakeExecutor:
    def __init__(self, cases: CaseStore, clock=None, scheduler=None):
        self.cases = cases
        self.clock = clock
        self.scheduler = scheduler

    def _now(self) -> datetime:
        return self.clock.now() if self.clock is not None else datetime.now(timezone.utc)

    def execute(self, wake: Wake, trigger: dict[str, Any] | None = None) -> dict:
        case = self.cases.get(wake.run_id)
        if case is None:
            raise ValueError(f"wake references missing case {wake.run_id}")
        completed = case.setdefault("background_executions", [])
        existing = next((row for row in completed if row["wake_id"] == wake.wake_id), None)
        if existing:
            return existing
        now = self._now()
        if wake.kind == "courier_status_poll":
            courier = poll_sandbox_courier(case)
            if courier["status"] == "delivered":
                confirm_delivery(case, source="courier", wake_id=wake.wake_id, at=now)
                outcome = "case_closed"
                if self.scheduler is not None:
                    remaining = self.scheduler.cancel_kind(case["case_id"], "receipt_followup", "case resolved by courier confirmation")
                    case.setdefault("cancelled_wakes", []).extend(remaining)
            else:
                outcome = "no_longer_needed"
        elif wake.kind == "review_followup":
            outcome = "still_waiting" if case.get("review", {}).get("status") == "pending_human" else "no_longer_needed"
            if outcome == "still_waiting":
                _append(case, ACTOR, "Review follow-up due", "The unresolved case was surfaced in the synthetic backup queue; no clinical decision was made.", status="attention", evidence_ids=[wake.wake_id], at=now)
        elif wake.kind == "receipt_followup":
            outcome = "still_waiting" if case.get("delivery", {}).get("status") == "dispatched" else "no_longer_needed"
            if outcome == "still_waiting":
                _append(case, ACTOR, "Receipt follow-up due", "The sandbox delivery remains unconfirmed; no duplicate courier was dispatched.", status="attention", evidence_ids=[wake.wake_id], at=now)
        elif wake.kind == "outage_watch":
            from cold_clock.followups import register_followups
            from cold_clock.outage import evaluate_outage_watch, register_outage_watch

            attempt = int((wake.payload or {}).get("attempt", 0))
            outcome = evaluate_outage_watch(case, now, wake.wake_id, attempt)
            if outcome == "recheck":
                register_outage_watch(case, self.scheduler, attempt + 1)
            elif outcome == "excursion_recorded":
                register_followups(case, self.scheduler)
        else:
            raise ValueError(f"unsupported ColdClock wake kind {wake.kind}")
        action = {
            "wake_id": wake.wake_id,
            "kind": wake.kind,
            "outcome": outcome,
            "external_contact": False,
            "fired_at": now.isoformat(),
            "trigger": (trigger or {}).get("mode", "direct"),
            "trigger_identity": (trigger or {}).get("email"),
            "attempt": wake.attempts,
        }
        completed.append(action)
        # Backwards-compatible alias used by earlier proofs.
        case.setdefault("wake_actions", []).append(action)
        self.cases.put(case)
        return action
