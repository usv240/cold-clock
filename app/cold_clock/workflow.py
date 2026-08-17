"""Deterministic, safety-bounded ColdClock workflow.

The public demo uses synthetic data and recorded model evidence. Clinical authority stays with a
human reviewer; the state machine makes it impossible to fulfill before that approval.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

BASE_TIME = datetime(2026, 8, 16, 14, 0, tzinfo=timezone.utc)
ALLOWED_DISPOSITIONS = {
    "continue_labeled",
    "shorten_window",
    "clinical_monitoring",
    "replace",
    "manufacturer_review",
}

PACKAGE_TRANSCRIPTION = """INSULIN GLARGINE-YFGN INJECTION
100 units/mL (U-100)
10 mL multiple-dose vial
Rx only
Lot DEMO-2048
Opened 2026-08-12
Synthetic demonstration package — not for human use"""

LABEL_EVIDENCE = {
    "source_id": "dailymed-insulin-glargine-yfgn",
    "title": "DailyMed: Insulin Glargine-yfgn injection",
    "url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?audience=consumer&setid=72cfe377-52f6-0348-fc71-5d4ac1992ffb",
    "retrieved_on": "2026-08-16",
    "jurisdiction": "United States",
    "quoted_storage_text": (
        "Store unused Insulin Glargine-yfgn in a refrigerator between 2° to 8°C "
        "(36° to 46°F)."
    ),
    "bounded_interpretation": (
        "The observed synthetic excursion is outside the quoted refrigerated range. "
        "This does not determine whether the medicine may be used."
    ),
}


def _case_base(case: dict[str, Any]) -> datetime:
    value = str(case.get("created_at") or _iso(BASE_TIME))
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


def _case_moment(case: dict[str, Any], minutes: int) -> datetime:
    if case.get("clock_mode") == "realtime":
        return datetime.now(timezone.utc)
    return _case_base(case) + timedelta(minutes=minutes)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _append(
    case: dict[str, Any],
    actor: str,
    action: str,
    detail: str,
    status: str = "complete",
    evidence_ids: list[str] | None = None,
) -> None:
    case["timeline"].append(
        {
            "sequence": len(case["timeline"]) + 1,
            "at": _iso(_case_moment(case, len(case["timeline"]) * 4)),
            "actor": actor,
            "action": action,
            "detail": detail,
            "status": status,
            "evidence_ids": evidence_ids or [],
        }
    )


def create_case() -> dict[str, Any]:
    case_id = f"cc-{uuid4().hex}"
    case: dict[str, Any] = {
        "case_id": case_id,
        "synthetic": True,
        "status": "monitoring",
        "created_at": _iso(BASE_TIME),
        "household": {
            "display_name": "Morgan — synthetic household",
            "contact_preference": "text",
            "mobility_note": "No private vehicle during the demonstration outage.",
        },
        "medication": {
            "display_name": "Insulin glargine-yfgn",
            "strength": "100 units/mL",
            "form": "10 mL multiple-dose vial",
            "lot": "DEMO-2048",
            "opened_on": "2026-08-12",
            "package_is_synthetic": True,
        },
        "extraction": {
            "model": "gemini-3.5-flash",
            "mode": "recorded-replay",
            "transcription": PACKAGE_TRANSCRIPTION,
            "fields": [
                {"key": "name", "value": "Insulin glargine-yfgn", "quote": "INSULIN GLARGINE-YFGN INJECTION", "verified": True},
                {"key": "strength", "value": "100 units/mL", "quote": "100 units/mL (U-100)", "verified": True},
                {"key": "form", "value": "10 mL multiple-dose vial", "quote": "10 mL multiple-dose vial", "verified": True},
                {"key": "lot", "value": "DEMO-2048", "quote": "Lot DEMO-2048", "verified": True},
            ],
            "accuracy": {"matched": 4, "total": 4, "invented": 0},
        },
        "label_evidence": deepcopy(LABEL_EVIDENCE),
        "sensor": {
            "source": "synthetic battery-backed sensor",
            "state": "normal",
            "readings": [
                {"at": _iso(BASE_TIME), "fahrenheit": 41.0, "power": "on"},
            ],
        },
        "excursion": None,
        "review": {"status": "not_requested", "decision": None},
        "fulfillment": {"status": "not_started"},
        "delivery": {"status": "not_started"},
        "safety": {
            "clinical_decision_by_ai": False,
            "outbound_actions_sandboxed": True,
            "disclosure": (
                "ColdClock organizes evidence and logistics. A qualified professional decides "
                "whether medicine may be used, monitored, or replaced."
            ),
        },
        "timeline": [],
    }
    _append(
        case,
        "Intake agent",
        "Package verified",
        "Four package fields retained because each value has an exact transcription quote.",
        evidence_ids=["synthetic-package", LABEL_EVIDENCE["source_id"]],
    )
    _append(
        case,
        "Monitor agent",
        "Monitoring active",
        "Battery-backed synthetic sensor is reporting within the refrigerated range.",
    )
    return case


def trigger_outage(case: dict[str, Any]) -> dict[str, Any]:
    if case["status"] != "monitoring":
        raise ValueError("outage can only be triggered from monitoring")
    readings = [
        {"at": _iso(_case_moment(case, 20)), "fahrenheit": 47.8, "power": "off"},
        {"at": _iso(_case_moment(case, 75)), "fahrenheit": 68.4, "power": "off"},
        {"at": _iso(_case_moment(case, 165)), "fahrenheit": 95.2, "power": "off"},
    ]
    case["sensor"]["state"] = "excursion"
    case["sensor"]["readings"].extend(readings)
    case["excursion"] = {
        "started_at": readings[0]["at"],
        "observed_minutes": 145,
        "minimum_fahrenheit": 47.8,
        "maximum_fahrenheit": 95.2,
        "power_event": "utility outage fixture",
        "assessment": "professional_review_required",
        "ai_disposition": None,
    }
    case["status"] = "excursion_detected"
    _append(
        case,
        "Excursion agent",
        "Excursion recorded",
        "Observed time and temperature were calculated; no use-or-discard decision was made.",
        status="attention",
        evidence_ids=[LABEL_EVIDENCE["source_id"], "sensor-readings"],
    )
    return case


def request_review(case: dict[str, Any]) -> dict[str, Any]:
    if case["status"] != "excursion_detected":
        raise ValueError("review requires a recorded excursion")
    case["review"] = {
        "status": "pending_human",
        "requested_at": _iso(_case_moment(case, 169)),
        "packet": {
            "medicine": case["medication"]["display_name"],
            "package_fields_verified": case["extraction"]["accuracy"]["matched"],
            "observed_minutes": case["excursion"]["observed_minutes"],
            "maximum_fahrenheit": case["excursion"]["maximum_fahrenheit"],
            "opened_on": case["medication"]["opened_on"],
            "source_url": case["label_evidence"]["url"],
            "question": "What reviewed disposition should govern this synthetic case?",
        },
        "decision": None,
    }
    case["status"] = "awaiting_professional_review"
    _append(
        case,
        "Review packet agent",
        "Human review requested",
        "A bounded packet was routed to the synthetic pharmacist workspace.",
        status="waiting",
        evidence_ids=[LABEL_EVIDENCE["source_id"], "sensor-readings"],
    )
    return case


def record_review(
    case: dict[str, Any],
    disposition: str,
    reviewer_name: str,
    rationale: str,
) -> dict[str, Any]:
    if case["review"]["status"] != "pending_human":
        raise ValueError("a pending human review is required")
    if disposition not in ALLOWED_DISPOSITIONS:
        raise ValueError("unsupported reviewed disposition")
    if len(reviewer_name.strip()) < 3 or len(rationale.strip()) < 8:
        raise ValueError("reviewer and rationale are required")
    case["review"] = {
        **case["review"],
        "status": "approved",
        "decision": {
            "disposition": disposition,
            "reviewer": reviewer_name.strip(),
            "reviewer_role": "synthetic pharmacist reviewer",
            "rationale": rationale.strip(),
            "decided_at": _iso(_case_moment(case, 174)),
            "made_by_ai": False,
        },
    }
    case["status"] = "replacement_approved" if disposition == "replace" else "review_resolved"
    _append(
        case,
        "Human reviewer",
        "Disposition approved",
        f"{reviewer_name.strip()} selected {disposition.replace('_', ' ')}. AI did not make this decision.",
        evidence_ids=[LABEL_EVIDENCE["source_id"], "review-decision"],
    )
    return case


def prepare_fulfillment(case: dict[str, Any]) -> dict[str, Any]:
    decision = case.get("review", {}).get("decision") or {}
    if case["status"] != "replacement_approved" or decision.get("disposition") != "replace":
        raise ValueError("replacement fulfillment requires an approved human replacement decision")
    case["fulfillment"] = {
        "status": "prepared",
        "sandbox": True,
        "pharmacy": "Northstar Community Pharmacy — synthetic",
        "inventory": "1 matching vial reserved in sandbox inventory",
        "coverage_path": "Emergency replacement request prepared for synthetic plan",
        "request_id": f"rx-{case['case_id'][3:]}",
        "approval_id": "review-decision",
    }
    case["status"] = "fulfillment_prepared"
    _append(
        case,
        "Fulfillment agent",
        "Replacement prepared",
        "Matching sandbox inventory was reserved after the human approval gate passed.",
        evidence_ids=["review-decision", "sandbox-inventory"],
    )
    return case


def dispatch_delivery(case: dict[str, Any]) -> dict[str, Any]:
    if case["fulfillment"].get("status") != "prepared":
        raise ValueError("a prepared replacement is required before dispatch")
    case["fulfillment"]["status"] = "confirmed"
    case["delivery"] = {
        "status": "dispatched",
        "sandbox": True,
        "courier": "AccessRoute Courier — synthetic",
        "delivery_id": f"dlv-{case['case_id'][3:]}",
        "eta_minutes": 34,
        "accessible_handoff": True,
    }
    case["status"] = "delivery_dispatched"
    _append(
        case,
        "Logistics agent",
        "Courier dispatched",
        "An accessible synthetic delivery slot was booked and linked to the approved replacement.",
        evidence_ids=["review-decision", "sandbox-inventory", "sandbox-delivery"],
    )
    return case


def confirm_delivery(case: dict[str, Any]) -> dict[str, Any]:
    if case["delivery"].get("status") != "dispatched":
        raise ValueError("a dispatched delivery is required")
    case["delivery"]["status"] = "received"
    case["delivery"]["received_at"] = _iso(_case_moment(case, 215))
    case["delivery"]["proof"] = "Synthetic household confirmation"
    case["status"] = "resolved"
    _append(
        case,
        "Household",
        "Replacement received",
        "The synthetic household confirmed receipt; the coordination case is closed.",
        evidence_ids=["sandbox-delivery", "receipt-confirmation"],
    )
    return case


def public_view(case: dict[str, Any]) -> dict[str, Any]:
    view = deepcopy(case)
    view["progress"] = {
        "current": case["status"],
        "completed_steps": len(case["timeline"]),
        "resolution_complete": case["status"] == "resolved",
        "clinical_authority": "human",
    }
    return view


def run_full_demo() -> dict[str, Any]:
    case = create_case()
    trigger_outage(case)
    request_review(case)
    record_review(
        case,
        "replace",
        "Avery Chen, PharmD — synthetic",
        "The documented demonstration excursion requires replacement in this tabletop case.",
    )
    prepare_fulfillment(case)
    dispatch_delivery(case)
    confirm_delivery(case)
    return public_view(case)

