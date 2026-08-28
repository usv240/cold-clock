"""Input-driven pilot API, separate from the deterministic public proof flow."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, HttpUrl

from cold_clock.followups import register_followups
from service.throttle import CASE_CREATES
from cold_clock.pilot import create_pilot_case, ingest_sensor_event
from cold_clock.store import CaseStore
from cold_clock.workflow import advance_safe_automation, public_view


class MedicationInput(BaseModel):
    display_name: str = Field(min_length=2, max_length=160)
    strength: str = Field(min_length=1, max_length=80)
    form: str = Field(min_length=2, max_length=120)
    lot: str = Field(min_length=1, max_length=80)
    opened_on: str = Field(default="Not provided", max_length=40)


class MonitoringRange(BaseModel):
    minimum: float
    maximum: float


class PilotCaseRequest(BaseModel):
    data_use_acknowledgement: Literal[True]
    data_class: Literal["synthetic", "deidentified-authorized"] = "synthetic"
    case_reference: str = Field(min_length=3, max_length=120)
    contact_preference: Literal["text", "voice", "email", "portal"] = "text"
    mobility_note: str = Field(default="", max_length=240)
    service_area: str = Field(default="grid-7", min_length=2, max_length=40, description="Utility service area used for outage fan-out.")
    medication: MedicationInput
    package_transcription: str = Field(min_length=10, max_length=4000)
    label_source_title: str = Field(min_length=3, max_length=180)
    label_source_url: HttpUrl
    jurisdiction: str = Field(min_length=2, max_length=80)
    quoted_storage_text: str = Field(min_length=10, max_length=1200)
    monitoring_range_f: MonitoringRange
    baseline_fahrenheit: float
    sensor_source: str = Field(min_length=3, max_length=160)


class SensorEventRequest(BaseModel):
    event_id: str = Field(min_length=3, max_length=120)
    started_at: str = Field(min_length=10, max_length=60)
    ended_at: str = Field(min_length=10, max_length=60)
    minimum_fahrenheit: float
    maximum_fahrenheit: float
    latest_fahrenheit: float
    power: Literal["on", "off", "unknown"]


def _summary(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "status": case["status"],
        "case_reference": case["household"]["display_name"],
        "medication": case["medication"]["display_name"],
        "origin": case.get("origin", "sample_fixture"),
        "data_class": case.get("data_class", "synthetic"),
        "created_at": case["created_at"],
        "latest_fahrenheit": case["sensor"]["readings"][-1].get("fahrenheit"),
        # Untouched: nothing has happened yet, so it is a clean start for a first-time visitor.
        "pristine": case["status"] == "monitoring" and not case.get("background_executions") and not case.get("utility_outage") and not case.get("excursion"),
    }


def build_pilot_router(store: CaseStore, scheduler=None, *, allow_deidentified: bool = False) -> APIRouter:
    router = APIRouter(prefix="/api/pilot", tags=["cold-clock-pilot"])

    @router.get("/cases")
    def list_cases() -> dict[str, Any]:
        cases = store.list_cases()
        return {"cases": [_summary(case) for case in cases], "count": len(cases)}

    @router.post("/cases")
    def open_pilot_case(request: PilotCaseRequest, http_request: Request, response: Response) -> dict[str, Any]:
        CASE_CREATES.guard(http_request, response)
        if request.data_class == "deidentified-authorized" and not allow_deidentified:
            raise HTTPException(
                status_code=403,
                detail="authorized de-identified intake requires a protected pilot deployment",
            )
        try:
            case = create_pilot_case(request.model_dump(mode="json"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        store.put(case)
        return public_view(case)

    @router.post("/cases/{case_id}/sensor-events")
    def sensor_event(case_id: str, request: SensorEventRequest) -> dict[str, Any]:
        case = store.get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"no ColdClock case {case_id}")
        try:
            ingest_sensor_event(case, request.model_dump())
            advance_safe_automation(case)
            register_followups(case, scheduler)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        store.put(case)
        return public_view(case)

    @router.get("/readiness")
    def readiness() -> dict[str, Any]:
        return {
            "level": "authorized de-identified pilot" if allow_deidentified else "public synthetic operational pilot",
            "working_now": [
                "multiple durable cases",
                "verbatim package evidence intake",
                "configured label source and monitoring range",
                "idempotent sensor-event ingestion",
                "human-only disposition gate",
                "ordered audit timeline",
            ],
            "required_before_phi_or_clinical_use": [
                "customer-specific identity and tenant isolation",
                "executed BAA and HIPAA risk assessment where applicable",
                "validated sensor and pharmacy connectors",
                "clinical safety and human-factors validation",
                "incident response, retention, backup, and recovery policies",
                "regulatory classification review",
            ],
            "claim": "ColdClock is not represented as production clinical software.",
            "public_data_policy": "synthetic-only" if not allow_deidentified else "authorized de-identified pilot",
        }

    return router
