"""HTTP contract for the ColdClock demonstration and acceptance flow."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cold_clock.followups import register_followups
from cold_clock.store import CaseStore
from spine.public_trace import public_action_trace
from cold_clock.workflow import (
    ALLOWED_DISPOSITIONS,
    advance_safe_automation,
    confirm_delivery,
    create_case,
    dispatch_delivery,
    prepare_fulfillment,
    public_view,
    record_review,
    request_review,
    run_full_demo,
    run_unattended_demo,
    trigger_outage,
)


class ReviewRequest(BaseModel):
    disposition: str
    reviewer_name: str = Field(min_length=3, max_length=120)
    rationale: str = Field(min_length=8, max_length=800)


def build_router(store: CaseStore, scheduler=None, *, allow_global_reset: bool = False, model_runner=None) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["cold-clock"])

    def require(case_id: str) -> dict[str, Any]:
        case = store.get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"no ColdClock case {case_id}")
        return case

    def mutate(case_id: str, operation: Any) -> dict[str, Any]:
        case = require(case_id)
        try:
            operation(case)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        store.put(case)
        return public_view(case)

    @router.get("/research")
    def research() -> dict[str, Any]:
        return {
            "claim_boundary": (
                "The sources establish the problem and relevant professional workflow. "
                "They do not validate ColdClock or prove outcome improvement."
            ),
            "sources": [
                {
                    "title": "FDA — Safe Drug Use After a Natural Disaster",
                    "url": "https://www.fda.gov/drugs/emergency-preparedness-drugs/safe-drug-use-after-natural-disaster",
                    "use": "Problem framing and requirement for professional or manufacturer guidance.",
                    "class": "U.S. public guidance",
                },
                {
                    "title": "CDC — Managing Insulin in an Emergency",
                    "url": "https://www.cdc.gov/diabetes/articles/managing-insulin-in-emergency.html",
                    "use": "Emergency storage precautions and clinical-escalation language.",
                    "class": "U.S. public guidance",
                },
                {
                    "title": "Cochrane — Thermal stability and storage of human insulin",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/37930742/",
                    "use": "Evidence that stability varies and universal rules are inappropriate.",
                    "class": "systematic review",
                },
                {
                    "title": "QChainMED home monitoring pilot",
                    "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13039186/",
                    "use": "Feasibility of continuous monitoring and explicit prior-art boundary.",
                    "class": "pilot study",
                },
                {
                    "title": "NHS SPS — Managing temperature excursions",
                    "url": "https://sps.nhs.uk/articles/managing-temperature-excursions/",
                    "use": "Professional workflow inspiration; not represented as U.S. authority.",
                    "class": "non-U.S. professional guidance",
                },
                {
                    "title": "DailyMed — Insulin Glargine-yfgn",
                    "url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?audience=consumer&setid=72cfe377-52f6-0348-fc71-5d4ac1992ffb",
                    "use": "Current structured label evidence for the synthetic fixture.",
                    "class": "U.S. structured label",
                },
            ],
        }

    @router.post("/cases")
    def open_case() -> dict[str, Any]:
        case = create_case()
        store.put(case)
        return public_view(case)

    @router.get("/cases/{case_id}")
    def get_case(case_id: str) -> dict[str, Any]:
        return public_view(require(case_id))

    @router.get("/cases/{case_id}/trace")
    def get_case_trace(case_id: str) -> dict[str, Any]:
        return public_action_trace(require(case_id), "case_id")

    @router.get("/cases/{case_id}/autonomy-proof")
    def get_case_autonomy_proof(case_id: str) -> dict[str, Any]:
        return public_view(require(case_id))["autonomy_proof"]

    @router.get("/cases/{case_id}/wakes")
    def get_case_wakes(case_id: str) -> dict[str, Any]:
        """Durable wake rows for a case: what the Cloud Scheduler worker will do, did, or cancelled."""
        require(case_id)
        if scheduler is None:
            return {"case_id": case_id, "wakes": [], "scan_cadence": "none"}
        rows = scheduler._store.for_run(case_id)
        return {
            "case_id": case_id,
            "simulated_now": scheduler.clock.now().isoformat(),
            "scan_cadence": "Cloud Scheduler calls /internal/wakes/scan every minute with a Google-signed OIDC token",
            "wakes": [
                {
                    "wake_id": row.wake_id,
                    "kind": row.kind,
                    "status": row.status.value,
                    "attempts": row.attempts,
                    "due_at": row.due_at.isoformat(),
                    "cancelled_reason": row.cancelled_reason,
                    "last_error": row.last_error,
                }
                for row in rows
            ],
        }

    @router.post("/cases/{case_id}/autopilot")
    def autopilot(case_id: str) -> dict[str, Any]:
        """Resume all currently safe work and stop at the next external or authority event."""
        def resume(case: dict[str, Any]) -> None:
            advance_safe_automation(case)
            register_followups(case, scheduler)

        return mutate(case_id, resume)
    @router.post("/cases/{case_id}/outage")
    def outage(case_id: str) -> dict[str, Any]:
        def handle_event(case: dict[str, Any]) -> None:
            trigger_outage(case)
            advance_safe_automation(case)
            register_followups(case, scheduler)

        return mutate(case_id, handle_event)

    @router.post("/cases/{case_id}/request-review")
    def review_request(case_id: str) -> dict[str, Any]:
        return mutate(case_id, request_review)

    @router.post("/cases/{case_id}/review")
    def review(case_id: str, request: ReviewRequest) -> dict[str, Any]:
        def apply_review_and_resume(case: dict[str, Any]) -> None:
            record_review(case, request.disposition, request.reviewer_name, request.rationale)
            advance_safe_automation(case)
            register_followups(case, scheduler)

        return mutate(case_id, apply_review_and_resume)

    @router.post("/cases/{case_id}/fulfillment")
    def fulfillment(case_id: str) -> dict[str, Any]:
        return mutate(case_id, prepare_fulfillment)

    @router.post("/cases/{case_id}/dispatch")
    def dispatch(case_id: str) -> dict[str, Any]:
        return mutate(case_id, dispatch_delivery)

    @router.post("/cases/{case_id}/confirm-delivery")
    def delivery(case_id: str) -> dict[str, Any]:
        return mutate(case_id, confirm_delivery)

    @router.post("/demo/full")
    def full_demo() -> dict[str, Any]:
        case = create_case()
        if model_runner is not None:
            try:
                model_runner.apply(case)
            except Exception as exc:
                raise HTTPException(status_code=503, detail="live model evidence unavailable; no replay substituted") from exc
        case = run_full_demo(case)
        store.put(case)
        return case

    @router.post("/demo/unattended")
    def unattended_demo() -> dict[str, Any]:
        """Run every safe transition and stop at the courier ETA.

        The receipt is deliberately not fabricated here. A durable ``courier_status_poll`` wake is
        registered; the Cloud Scheduler worker polls the sandbox courier at the ETA and closes the
        case with nobody at the screen. Poll ``GET /api/cases/{case_id}`` to watch it happen.
        """
        case = create_case()
        if model_runner is not None:
            try:
                model_runner.apply(case)
            except Exception as exc:
                raise HTTPException(status_code=503, detail="live model evidence unavailable; no replay substituted") from exc
        run_unattended_demo(case)
        register_followups(case, scheduler)
        store.put(case)
        return public_view(case)

    @router.get("/model-evidence")
    def model_evidence() -> dict[str, Any]:
        return {
            "execution": "POST /api/demo/full and POST /api/demo/unattended return live, fail-closed model receipts",
            "models": [
                {"name": "gemini-3.5-flash", "purpose": "quote-grounded synthetic artifact extraction", "docs": "https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-5-flash"},
                {"name": "gemini-embedding-001", "purpose": "semantic evidence routing without authority decisions", "docs": "https://docs.cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings"},
                {"name": "gemma-4-26b-a4b-it-maas", "purpose": "second-layer prompt-injection screen on untrusted package text; receipt in injection_screen", "docs": "https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/gemma"},
            ],
            "replay_policy": "recorded outputs are test-only; deployed full workflows do not silently substitute them",
            "degradation_policy": "extraction and routing fail closed; the Gemma screen reports live=false and the deterministic pattern layer stands alone",
        }

    @router.post("/reset")
    def reset() -> dict[str, Any]:
        if not allow_global_reset:
            raise HTTPException(status_code=403, detail="global reset is disabled in this deployment")
        store.clear()
        return {"ok": True}

    @router.get("/proof")
    def proof() -> dict[str, Any]:
        checks: list[dict[str, Any]] = []

        def check(name: str, passed: bool, detail: str = "") -> None:
            checks.append({"check": name, "pass": bool(passed), "detail": detail})

        case = create_case()
        check(
            "every extracted field is quote-grounded",
            all(row["quote"] in case["extraction"]["transcription"] for row in case["extraction"]["fields"]),
        )
        try:
            prepare_fulfillment(case)
            blocked = False
        except ValueError:
            blocked = True
        check("fulfillment before human review is blocked", blocked)
        trigger_outage(case)
        check("excursion contains no AI disposition", case["excursion"]["ai_disposition"] is None)
        request_review(case)
        try:
            record_review(case, "invented", "Reviewer Name", "A sufficiently long rationale.")
            unsupported_blocked = False
        except ValueError:
            unsupported_blocked = True
        check("unsupported disposition is rejected", unsupported_blocked)
        record_review(case, "replace", "Avery Chen, PharmD — synthetic", "Replacement approved for this tabletop demonstration.")
        check("human decision is explicitly not AI", not case["review"]["decision"]["made_by_ai"])
        prepare_fulfillment(case)
        dispatch_delivery(case)
        confirm_delivery(case)
        check("approved workflow reaches receipt proof", case["delivery"]["status"] == "received")
        check("outbound integrations are labelled sandbox", case["fulfillment"]["sandbox"] and case["delivery"]["sandbox"])
        check("timeline preserves ordered evidence", [row["sequence"] for row in case["timeline"]] == list(range(1, len(case["timeline"]) + 1)))
        return {
            "passed": sum(row["pass"] for row in checks),
            "total": len(checks),
            "checks": checks,
            "allowed_human_dispositions": sorted(ALLOWED_DISPOSITIONS),
        }

    @router.get("/conformance")
    def conformance() -> dict[str, Any]:
        return {
            "category": "The Taskmaster",
            "requirements": [
                {
                    "requirement": "complete workflow rather than text generation",
                    "implementation": "event -> evidence -> approval -> fulfillment -> delivery -> receipt",
                    "proof": "/api/proof and tests/test_workflow.py",
                },
                {
                    "requirement": "takes action",
                    "implementation": "sandbox inventory reservation and courier dispatch after approval",
                    "proof": "timeline and executable demo flow",
                },
                {
                    "requirement": "runs asynchronously in the background",
                    "implementation": "Cloud Scheduler calls the OIDC-protected wake worker every minute; a durable courier_status_poll wake closes the case at the ETA",
                    "proof": "POST /api/demo/unattended then GET /api/cases/{case_id}/wakes and the autonomy proof's cloud_scheduler_triggered_executions",
                },
                {
                    "requirement": "Gemini 3.5 or newer",
                    "implementation": "Live fail-closed Gemini 3.5 Flash package reader plus Gemini Embedding 001 evidence routing",
                    "proof": "POST /api/demo/full model_execution and semantic_routing receipts; fixtures are test-only",
                },
                {
                    "requirement": "Google Cloud infrastructure",
                    "implementation": "Cloud Run, Firestore-compatible persistence, Vertex AI, Cloud Trace hooks",
                    "proof": "Dockerfile, deploy.sh, health endpoint, deployment recording",
                },
            ],
            "limitations": [
                "The public service accepts synthetic pilot evidence only; authorized de-identified mode requires a separate protected deployment.",
                "ColdClock does not make medication-use decisions.",
                "Recorded fixtures are test-only and must never be described as live calls.",
                "No clinical outcome claim has been validated.",
            ],
        }

    return router

