"""Failure lab, durable wakes, and exit proof for ColdClock."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cold_clock.failures import (
    choose_accessible_courier,
    mark_reviewer_unavailable,
    report_courier_unavailable,
    report_sensor_gap,
    report_stock_unavailable,
    resolve_matching_stock,
    resume_human_review,
)
from cold_clock.store import CaseStore, MemoryCaseStore
from cold_clock.wake_actions import ColdClockWakeExecutor
from cold_clock.workflow import (
    create_case,
    dispatch_delivery,
    prepare_fulfillment,
    public_view,
    record_review,
    request_review,
    trigger_outage,
)
from spine.clock import MemoryClockStateStore, SimulatedClock
from spine.wake import MemoryWakeStore, WakeScheduler


class HumanChoice(BaseModel):
    chosen_by: str = Field(min_length=3, max_length=120)


class AdvanceRequest(BaseModel):
    minutes: int = Field(gt=0, le=10080)


def build_hardening_router(store: CaseStore, scheduler: WakeScheduler, clock) -> APIRouter:
    router = APIRouter(prefix="/api/hardening", tags=["cold-clock-hardening"])
    executor = ColdClockWakeExecutor(store)

    def require(case_id: str):
        case = store.get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"no ColdClock case {case_id}")
        return case

    def mutate(case_id: str, operation):
        case = require(case_id)
        try:
            operation(case)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        store.put(case)
        return public_view(case)

    @router.post("/cases/{case_id}/sensor-gap")
    def sensor_gap(case_id: str):
        return mutate(case_id, report_sensor_gap)

    @router.post("/cases/{case_id}/request-review")
    def review_and_sleep(case_id: str):
        case = require(case_id)
        try:
            request_review(case)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        wake = scheduler.sleep_for(case_id, "review_followup", timedelta(minutes=30))
        case.setdefault("scheduled_wakes", []).append({"wake_id": wake.wake_id, "kind": wake.kind, "due_at": wake.due_at.isoformat()})
        store.put(case)
        return public_view(case)

    @router.post("/cases/{case_id}/reviewer-unavailable")
    def reviewer_unavailable(case_id: str):
        return mutate(case_id, mark_reviewer_unavailable)

    @router.post("/cases/{case_id}/resume-review")
    def resume_review(case_id: str):
        return mutate(case_id, resume_human_review)

    @router.post("/cases/{case_id}/stock-unavailable")
    def stock_unavailable(case_id: str):
        return mutate(case_id, report_stock_unavailable)

    @router.post("/cases/{case_id}/resolve-stock")
    def resolve_stock(case_id: str):
        return mutate(case_id, resolve_matching_stock)

    @router.post("/cases/{case_id}/courier-unavailable")
    def courier_unavailable(case_id: str):
        return mutate(case_id, report_courier_unavailable)

    @router.post("/cases/{case_id}/choose-courier")
    def choose_courier(case_id: str, request: HumanChoice):
        return mutate(case_id, lambda case: choose_accessible_courier(case, request.chosen_by))

    @router.post("/cases/{case_id}/dispatch")
    def dispatch_and_sleep(case_id: str):
        case = require(case_id)
        try:
            dispatch_delivery(case)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        wake = scheduler.sleep_for(case_id, "receipt_followup", timedelta(minutes=60))
        case.setdefault("scheduled_wakes", []).append({"wake_id": wake.wake_id, "kind": wake.kind, "due_at": wake.due_at.isoformat()})
        store.put(case)
        return public_view(case)

    @router.get("/cases/{case_id}/wakes")
    def wakes(case_id: str):
        require(case_id)
        return {"wakes": [
            {"wake_id": row.wake_id, "kind": row.kind, "status": row.status.value, "attempts": row.attempts, "due_at": row.due_at.isoformat(), "last_error": row.last_error}
            for row in scheduler._store.for_run(case_id)
        ]}

    @router.post("/advance")
    def advance(request: AdvanceRequest):
        now = clock.advance(timedelta(minutes=request.minutes))
        dispatched = scheduler.dispatch_due(executor.execute)
        return {"simulated": True, "now": now.isoformat(), "dispatched": [row.wake_id for row in dispatched]}

    @router.post("/scan-due")
    def scan_due():
        dispatched = scheduler.dispatch_due(executor.execute)
        return {"dispatched": [row.wake_id for row in dispatched], "dead_letters": [row.wake_id for row in scheduler.dead_letters]}

    @router.get("/proof")
    def proof():
        checks = []
        def check(name, value): checks.append({"check": name, "pass": bool(value)})
        sensor = create_case(); report_sensor_gap(sensor)
        check("sensor gap creates safe stop", sensor["status"] == "evidence_incomplete" and sensor["safe_stop"]["system_disposition"] is None)
        review = create_case(); trigger_outage(review); request_review(review); mark_reviewer_unavailable(review)
        check("reviewer failure preserves no disposition", review["status"] == "review_escalated" and review["review"]["decision"] is None)
        resume_human_review(review); record_review(review, "replace", "Avery Chen — synthetic", "Human-reviewed replacement in tabletop fixture.")
        report_stock_unavailable(review)
        check("stock miss never substitutes", review["fulfillment"]["system_substitution"] is None)
        resolve_matching_stock(review); prepare_fulfillment(review); report_courier_unavailable(review)
        check("courier failure selects no option", review["delivery"]["system_selected_alternative"] is None)
        choose_accessible_courier(review, "Morgan — synthetic")
        check("human selects recovery", review["delivery"]["selected_by_ai"] is False)
        local_cases = MemoryCaseStore(); timed = create_case(); trigger_outage(timed); request_review(timed); local_cases.put(timed)
        local_clock = SimulatedClock(MemoryClockStateStore()); local_scheduler = WakeScheduler(MemoryWakeStore(), local_clock)
        first = local_scheduler.sleep_for(timed["case_id"], "review_followup", timedelta(minutes=30)); second = local_scheduler.sleep_for(timed["case_id"], "review_followup", timedelta(minutes=30))
        check("wake registration is idempotent", first.wake_id == second.wake_id)
        local_clock.advance(timedelta(minutes=31)); dispatched = local_scheduler.dispatch_due(ColdClockWakeExecutor(local_cases).execute)
        check("due wake fires exactly once", len(dispatched) == 1 and not local_scheduler.dispatch_due(ColdClockWakeExecutor(local_cases).execute))
        check("wake action sends no external contact", local_cases.get(timed["case_id"])["wake_actions"][0]["external_contact"] is False)
        return {"passed": sum(row["pass"] for row in checks), "total": len(checks), "checks": checks}

    return router
