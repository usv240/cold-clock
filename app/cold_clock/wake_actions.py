"""Idempotent ColdClock wake actions for reviewer and receipt follow-up."""

from __future__ import annotations

from cold_clock.store import CaseStore
from cold_clock.workflow import _append
from spine.wake import Wake


class ColdClockWakeExecutor:
    def __init__(self, cases: CaseStore):
        self.cases = cases

    def execute(self, wake: Wake) -> dict:
        case = self.cases.get(wake.run_id)
        if case is None:
            raise ValueError(f"wake references missing case {wake.run_id}")
        completed = case.setdefault("wake_actions", [])
        existing = next((row for row in completed if row["wake_id"] == wake.wake_id), None)
        if existing:
            return existing
        if wake.kind == "review_followup":
            outcome = "still_waiting" if case.get("review", {}).get("status") == "pending_human" else "no_longer_needed"
            if outcome == "still_waiting":
                _append(case, "Wake worker", "Review follow-up due", "The unresolved case was surfaced in the synthetic backup queue; no clinical decision was made.", status="attention", evidence_ids=[wake.wake_id])
        elif wake.kind == "receipt_followup":
            outcome = "still_waiting" if case.get("delivery", {}).get("status") == "dispatched" else "no_longer_needed"
            if outcome == "still_waiting":
                _append(case, "Wake worker", "Receipt follow-up due", "The sandbox delivery remains unconfirmed; no duplicate courier was dispatched.", status="attention", evidence_ids=[wake.wake_id])
        else:
            raise ValueError(f"unsupported ColdClock wake kind {wake.kind}")
        action = {"wake_id": wake.wake_id, "kind": wake.kind, "outcome": outcome, "external_contact": False}
        completed.append(action)
        self.cases.put(case)
        return action
