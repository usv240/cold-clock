"""Stable authenticated API for ColdClock integrations."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from cold_clock.followups import register_followups
from cold_clock.pilot import create_pilot_case, ingest_sensor_event
from cold_clock.store import CaseStore
from cold_clock.workflow import advance_safe_automation, confirm_delivery, public_view, record_review, run_full_demo, run_unattended_demo
from service.pilot_routes import PilotCaseRequest, SensorEventRequest
from service.routes import ReviewRequest
from spine.developer_access import DeveloperAccessManager, api_key_guard
from spine.public_trace import public_action_trace


def build_developer_router(store: CaseStore, access: DeveloperAccessManager, scheduler=None, *, allow_deidentified: bool = False, model_runner=None) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["ColdClock v1"], dependencies=[Depends(api_key_guard(access))])

    def require(case_id: str) -> dict[str, Any]:
        case = store.get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"no ColdClock case {case_id}")
        return case

    def save(case: dict[str, Any]) -> dict[str, Any]:
        store.put(case)
        return public_view(case)

    @router.post("/cases", status_code=201)
    def create(payload: PilotCaseRequest) -> dict[str, Any]:
        if payload.data_class == "deidentified-authorized" and not allow_deidentified:
            raise HTTPException(status_code=403, detail="de-identified intake requires a protected deployment")
        try:
            return save(create_pilot_case(payload.model_dump(mode="json")))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/cases/{case_id}")
    def read(case_id: str) -> dict[str, Any]:
        return public_view(require(case_id))

    @router.post("/cases/{case_id}/sensor-events")
    def sensor_event(case_id: str, payload: SensorEventRequest) -> dict[str, Any]:
        case = require(case_id)
        try:
            ingest_sensor_event(case, payload.model_dump())
            advance_safe_automation(case)
            register_followups(case, scheduler)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return save(case)

    @router.post("/cases/{case_id}/review-decisions")
    def review(case_id: str, payload: ReviewRequest) -> dict[str, Any]:
        case = require(case_id)
        try:
            record_review(case, payload.disposition, payload.reviewer_name, payload.rationale)
            advance_safe_automation(case)
            register_followups(case, scheduler)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return save(case)

    @router.post("/cases/{case_id}/receipt-events")
    def receipt(case_id: str) -> dict[str, Any]:
        case = require(case_id)
        try:
            confirm_delivery(case)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return save(case)

    @router.get("/cases/{case_id}/trace")
    def trace(case_id: str) -> dict[str, Any]:
        return public_action_trace(require(case_id), "case_id")

    @router.get("/cases/{case_id}/autonomy-proof")
    def autonomy(case_id: str) -> dict[str, Any]:
        return public_view(require(case_id))["autonomy_proof"]

    @router.post("/tabletop-runs", status_code=201)
    def tabletop() -> dict[str, Any]:
        from cold_clock.workflow import create_case
        case = create_case()
        if model_runner is not None:
            try:
                model_runner.apply(case)
            except Exception as exc:
                raise HTTPException(status_code=503, detail="live Gemini evidence unavailable; no replay substituted") from exc
        result = run_full_demo(case)
        store.put(case)
        return result

    @router.post("/unattended-runs", status_code=201)
    def unattended() -> dict[str, Any]:
        """Run every safe transition, then leave closure to the Cloud Scheduler wake worker."""
        from cold_clock.workflow import create_case
        case = create_case()
        if model_runner is not None:
            try:
                model_runner.apply(case)
            except Exception as exc:
                raise HTTPException(status_code=503, detail="live Gemini evidence unavailable; no replay substituted") from exc
        run_unattended_demo(case)
        register_followups(case, scheduler)
        return save(case)

    return router
