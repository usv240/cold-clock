"""Deterministic, safety-bounded ColdClock workflow.

The public demo uses synthetic data and recorded model evidence. Clinical authority stays with a
human reviewer; the state machine makes it impossible to fulfill before that approval.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
from spine.autonomy_proof import build_autonomy_proof

BASE_TIME = datetime(2026, 8, 16, 14, 0, tzinfo=timezone.utc)
DEFAULT_COURIER_ETA_MINUTES = 34
DEFAULT_SERVICE_AREA = "grid-7"
MAX_COURIER_REPOLLS = 3
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
Synthetic demonstration package: not for human use"""

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
    at: datetime | None = None,
) -> None:
    case["timeline"].append(
        {
            "sequence": len(case["timeline"]) + 1,
            "at": _iso(at) if at is not None else _iso(_case_moment(case, len(case["timeline"]) * 4)),
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
        "opened_at": _iso(datetime.now(timezone.utc)),
        "service_area": DEFAULT_SERVICE_AREA,
        "household": {
            "display_name": "Morgan (synthetic household)",
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


PACKET_AGENT: Any | None = None


def request_review(case: dict[str, Any]) -> dict[str, Any]:
    if case["status"] != "excursion_detected":
        raise ValueError("review requires a recorded excursion")
    from cold_clock.packet_agent import assemble_packet

    packet, receipt = assemble_packet(case, PACKET_AGENT)
    case["review"] = {
        "status": "pending_human",
        "requested_at": _iso(_case_moment(case, 169)),
        "packet": packet,
        "decision": None,
    }
    case["packet_agent"] = receipt
    case["status"] = "awaiting_professional_review"
    if receipt.get("live") and receipt.get("accepted"):
        detail = (
            f"The ADK review-packet agent called {len(receipt['tool_calls'])} scoped read-only tools; the verifier "
            f"confirmed all {len(receipt['verified_fields'])} packet values against tool output before routing."
        )
    elif receipt.get("live"):
        detail = (
            f"The ADK review-packet agent's output was rejected ({', '.join(receipt.get('rejected_fields') or ['missing tool call'])}); "
            "the deterministic packet was routed instead."
        )
    else:
        detail = "A bounded packet was routed to the synthetic pharmacist workspace."
    _append(
        case,
        "Review packet agent",
        "Human review requested",
        detail,
        status="waiting",
        evidence_ids=[LABEL_EVIDENCE["source_id"], "sensor-readings", *(["packet-agent-receipt"] if receipt.get("live") else [])],
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
        "pharmacy": "Northstar Community Pharmacy (synthetic)",
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
    eta_minutes = int(case.get("delivery_eta_minutes") or DEFAULT_COURIER_ETA_MINUTES)
    case["fulfillment"]["status"] = "confirmed"
    case["delivery"] = {
        "status": "dispatched",
        "sandbox": True,
        "courier": "AccessRoute Courier (synthetic)",
        "delivery_id": f"dlv-{case['case_id'][3:]}",
        "eta_minutes": eta_minutes,
        "dispatched_at": _iso(_case_moment(case, 181)),
        "accessible_handoff": True,
        "background_status_poll": "courier_status_poll wake due at the sandbox ETA",
        # The sandbox courier is a stateful connector, not a timer: each poll is answered from this
        # job record, and a delay (see the failure lab) makes it report in_transit instead.
        "courier_job": {"status": "in_transit", "polls": 0, "delay_polls": int(case.get("courier_delay_polls") or 0), "history": []},
    }
    case["status"] = "delivery_dispatched"
    _append(
        case,
        "Logistics agent",
        "Courier dispatched",
        "An accessible synthetic delivery slot was booked and linked to the approved replacement. "
        "A durable wake will poll the sandbox courier at the ETA.",
        evidence_ids=["review-decision", "sandbox-inventory", "sandbox-delivery"],
    )
    return case


def confirm_delivery(
    case: dict[str, Any],
    *,
    source: str = "household",
    wake_id: str | None = None,
    at: datetime | None = None,
) -> dict[str, Any]:
    """Close the case with receipt evidence.

    ``source`` is ``household`` for a receipt event supplied from outside, or ``courier`` when the
    background wake polled the sandbox courier at the ETA and it reported the handoff complete.
    Either way the closure is evidence-driven; the agent never invents a receipt.
    """
    if case["delivery"].get("status") != "dispatched":
        raise ValueError("a dispatched delivery is required")
    if source not in {"household", "courier"}:
        raise ValueError("unsupported receipt source")
    case["delivery"]["status"] = "received"
    case["delivery"]["received_at"] = _iso(at) if at is not None else _iso(_case_moment(case, 215))
    case["status"] = "resolved"
    if source == "courier":
        case["delivery"]["proof"] = "Sandbox courier delivery confirmation polled by background wake"
        case["delivery"]["confirmed_by"] = "background-wake"
        case["delivery"]["confirming_wake_id"] = wake_id
        _append(
            case,
            "Background wake agent",
            "Courier confirmed handoff",
            "The Cloud Scheduler wake polled the sandbox courier at the ETA; it reported the accessible "
            "handoff complete, so the case closed with no operator action.",
            evidence_ids=["sandbox-delivery", "courier-delivery-confirmation", *( [wake_id] if wake_id else [] )],
            at=at,
        )
        return case
    case["delivery"]["proof"] = "Synthetic household confirmation"
    case["delivery"]["confirmed_by"] = "household"
    _append(
        case,
        "Household",
        "Replacement received",
        "The synthetic household confirmed receipt; the coordination case is closed.",
        evidence_ids=["sandbox-delivery", "receipt-confirmation"],
    )
    return case


def advance_safe_automation(case: dict[str, Any]) -> list[str]:
    """Advance every transition that does not require new external evidence or authority."""
    actions: list[str] = []
    while True:
        if case["status"] == "excursion_detected":
            request_review(case)
            actions.append("review_packet_routed")
            continue
        if case["status"] == "replacement_approved":
            prepare_fulfillment(case)
            actions.append("replacement_reserved")
            continue
        if case["status"] == "fulfillment_prepared":
            dispatch_delivery(case)
            actions.append("accessible_delivery_dispatched")
            continue
        break
    case["last_autonomy_run"] = {
        "actions": actions,
        "stopped_at": case["status"],
        "waiting_for": {
            "monitoring": "sensor_event",
            "awaiting_professional_review": "qualified_human_disposition",
            "delivery_dispatched": "courier_confirmation_wake_or_household_receipt",
            "review_resolved": "no_further_logistics_required",
            "resolved": None,
        }.get(case["status"], "unsupported_state"),
    }
    case.setdefault("autonomy_runs", []).append(deepcopy(case["last_autonomy_run"]))
    return actions

def public_view(case: dict[str, Any]) -> dict[str, Any]:
    view = deepcopy(case)
    view["progress"] = {
        "current": case["status"],
        "completed_steps": len(case["timeline"]),
        "resolution_complete": case["status"] in {"resolved", "review_resolved"},
        "clinical_authority": "human",
    }
    background = case.get("background_executions") or []
    view["autonomy"] = {
        "trigger": "sensor or power event",
        "automatic_actions": [
            "verify evidence",
            "route review packet",
            "reserve approved replacement",
            "dispatch accessible delivery",
            "poll courier at ETA from a Cloud Scheduler wake",
        ],
        "authority_checkpoints": ["qualified medication disposition"],
        "external_completion_event": "courier handoff confirmation or household receipt",
        "current_wait": None
        if case["status"] in {"resolved", "review_resolved"}
        else (case.get("last_autonomy_run") or {}).get("waiting_for", "sensor_event"),
        "last_run_actions": (case.get("last_autonomy_run") or {}).get("actions", []),
        "complete": case["status"] in {"resolved", "review_resolved"},
        "background_wakes_fired": len(background),
        "closed_by_background_wake": (case.get("delivery") or {}).get("confirmed_by") == "background-wake",
        "pending_background_wakes": [
            row for row in (case.get("scheduled_wakes") or [])
            if row.get("wake_id") not in {item.get("wake_id") for item in background}
            and row.get("wake_id") not in set(case.get("cancelled_wakes") or [])
        ],
    }
    view["autonomy_proof"] = build_autonomy_proof(
        case,
        id_field="case_id",
        automatic_actors=("agent", "gateway", "pilot intake", "live evidence", "evidence gate", "review coordinator"),
        authority_actors=("pharmd", "reviewer", "human reviewer"),
        external_actors=("household", "sensor gateway", "utility outage"),
    )
    return view


def run_full_demo(case: dict[str, Any] | None = None) -> dict[str, Any]:
    case = case or create_case()
    trigger_outage(case)
    advance_safe_automation(case)
    record_review(
        case,
        "replace",
        "Avery Chen, PharmD (synthetic)",
        "The documented demonstration excursion requires replacement in this tabletop case.",
    )
    advance_safe_automation(case)
    confirm_delivery(case)
    case["demo_completion_mode"] = "synthetic_tabletop"
    return public_view(case)


def run_unattended_demo(case: dict[str, Any] | None = None, *, courier_eta_minutes: int = 1, stop_at_review: bool = False) -> dict[str, Any]:
    """Run every safe transition and then stop at the courier ETA.

    Unlike ``run_full_demo`` this never fabricates the receipt inside the request. The case is
    left in ``delivery_dispatched`` with a short sandbox ETA so the Cloud Scheduler wake worker,
    not the caller, is what polls the courier and closes the case.

    With ``stop_at_review`` the request stops at the human gate instead of recording the labelled
    synthetic pharmacist decision, so a real person enters the disposition and everything after
    that click: reservation, dispatch, and the scheduler-fired closure: is automatic.
    """
    case = case or create_case()
    case["delivery_eta_minutes"] = int(courier_eta_minutes)
    trigger_outage(case)
    advance_safe_automation(case)
    if stop_at_review:
        case["demo_completion_mode"] = "awaiting_real_review_then_background"
        return case
    record_review(
        case,
        "replace",
        "Avery Chen, PharmD (synthetic)",
        "The documented demonstration excursion requires replacement in this unattended case.",
    )
    advance_safe_automation(case)
    case["demo_completion_mode"] = "background_wake_pending"
    return case

