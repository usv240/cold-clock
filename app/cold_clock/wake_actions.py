"""Idempotent ColdClock wake actions executed by the Cloud Scheduler worker.

Four kinds exist:

* ``courier_status_poll`` fires at the sandbox courier ETA and asks the courier connector for the
  job's state. A confirmed handoff closes the case; ``in_transit`` re-arms the poll (bounded) and
  a courier that never confirms becomes a visible "delivery unconfirmed" hold for a human. The
  receipt is never invented from the clock.
* ``outage_watch`` judges a case from its own readings after a grid outage.
* ``review_followup`` surfaces a review that is still unresolved after thirty minutes.
* ``receipt_followup`` surfaces a delivery that is still unconfirmed after sixty minutes.

None of them makes a medication decision or contacts anyone outside the sandbox.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from cold_clock.store import CaseStore
from cold_clock.workflow import MAX_COURIER_REPOLLS, _append, confirm_delivery
from spine.wake import Wake

ACTOR = "Background wake agent"
COURIER_REPOLL_MINUTES = 1


def poll_sandbox_courier(case: dict[str, Any], now: datetime) -> dict[str, Any]:
    """The sandbox courier connector. Answers from the job record it was given at dispatch."""
    delivery = case.get("delivery") or {}
    if delivery.get("status") != "dispatched":
        return {"status": "not_in_transit", "sandbox": True}
    job = delivery.setdefault("courier_job", {"status": "in_transit", "polls": 0, "delay_polls": 0, "history": []})
    job["polls"] = int(job.get("polls", 0)) + 1
    delivered = job["polls"] > int(job.get("delay_polls", 0))
    job["status"] = "delivered" if delivered else "in_transit"
    job.setdefault("history", []).append({"at": now.isoformat(), "reported": job["status"]})
    return {"status": job["status"], "sandbox": True, "delivery_id": delivery.get("delivery_id"), "poll": job["polls"], "accessible_handoff": delivered}


class ColdClockWakeExecutor:
    def __init__(self, cases: CaseStore, clock=None, scheduler=None):
        self.cases = cases
        self.clock = clock
        self.scheduler = scheduler

    def _now(self) -> datetime:
        return self.clock.now() if self.clock is not None else datetime.now(timezone.utc)

    def _record_wake(self, case: dict[str, Any], wake) -> None:
        rows = case.setdefault("scheduled_wakes", [])
        if not any(row["wake_id"] == wake.wake_id for row in rows):
            rows.append({"wake_id": wake.wake_id, "kind": wake.kind, "due_at": wake.due_at.isoformat()})

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
            courier = poll_sandbox_courier(case, now)
            if courier["status"] == "delivered":
                confirm_delivery(case, source="courier", wake_id=wake.wake_id, at=now)
                outcome = "case_closed"
                if self.scheduler is not None:
                    remaining = self.scheduler.cancel_kind(case["case_id"], "receipt_followup", "case resolved by courier confirmation")
                    case.setdefault("cancelled_wakes", []).extend(remaining)
            elif courier["status"] == "in_transit":
                attempt = int((wake.payload or {}).get("repoll", 0))
                if attempt < MAX_COURIER_REPOLLS and self.scheduler is not None:
                    outcome = "in_transit_repoll"
                    _append(case, ACTOR, "Courier still in transit", f"The sandbox courier reported the delivery still in transit on poll {courier['poll']}; polling again in {COURIER_REPOLL_MINUTES} minute(s). No receipt was assumed.", status="attention", evidence_ids=[wake.wake_id, "sandbox-delivery"], at=now)
                    self._record_wake(case, self.scheduler.sleep_for(case["case_id"], "courier_status_poll", timedelta(minutes=COURIER_REPOLL_MINUTES), payload={"repoll": attempt + 1}, discriminator=f"repoll-{attempt + 1}"))
                else:
                    outcome = "delivery_unconfirmed_hold"
                    case["delivery"]["hold"] = {"reason": "courier never confirmed the handoff", "system_receipt": None, "next_authority": "household or pharmacy staff"}
                    _append(case, ACTOR, "Delivery unconfirmed: human follow-up", f"After {courier['poll']} polls the sandbox courier still had not confirmed the handoff. The case stays open for a person; no receipt was invented.", status="blocked", evidence_ids=[wake.wake_id, "sandbox-delivery"], at=now)
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
