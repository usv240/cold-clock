"""ColdClock safe-stop and recovery paths exercised by the public failure lab."""

from __future__ import annotations

from typing import Any

from cold_clock.workflow import _append


def report_sensor_gap(case: dict[str, Any]) -> dict[str, Any]:
    if case["status"] != "monitoring":
        raise ValueError("sensor gap can only be reported while monitoring")
    case["sensor"]["state"] = "evidence_gap"
    case["sensor"]["readings"].append(
        {"at": None, "fahrenheit": None, "power": "unknown", "missing": True}
    )
    case["status"] = "evidence_incomplete"
    case["safe_stop"] = {
        "reason": "temperature history is incomplete",
        "system_disposition": None,
        "next_authority": "qualified professional or manufacturer",
    }
    _append(
        case,
        "Evidence gate",
        "Incomplete sensor history stopped",
        "The system did not infer a temperature, duration, or medication disposition.",
        status="blocked",
        evidence_ids=["sensor-gap"],
    )
    return case


def mark_reviewer_unavailable(case: dict[str, Any]) -> dict[str, Any]:
    if case.get("review", {}).get("status") != "pending_human":
        raise ValueError("reviewer escalation requires a pending human review")
    case["review"]["status"] = "escalated_unavailable"
    case["review"]["escalation"] = {
        "route": "synthetic backup pharmacist queue",
        "external_message_sent": False,
        "system_disposition": None,
    }
    case["status"] = "review_escalated"
    _append(
        case,
        "Review coordinator",
        "Primary reviewer unavailable",
        "A sandbox backup route was prepared; medicine disposition remains unresolved.",
        status="attention",
        evidence_ids=["review-escalation"],
    )
    return case


def resume_human_review(case: dict[str, Any]) -> dict[str, Any]:
    if case["status"] != "review_escalated":
        raise ValueError("only an escalated review can resume")
    case["review"]["status"] = "pending_human"
    case["review"]["resumed_by"] = "synthetic backup pharmacist queue"
    case["status"] = "awaiting_professional_review"
    _append(
        case,
        "Review coordinator",
        "Human review resumed",
        "A qualified synthetic backup reviewer accepted the unchanged evidence packet.",
        evidence_ids=["review-escalation", "review-packet"],
    )
    return case


def report_stock_unavailable(case: dict[str, Any]) -> dict[str, Any]:
    decision = case.get("review", {}).get("decision") or {}
    if case["status"] != "replacement_approved" or decision.get("disposition") != "replace":
        raise ValueError("stock search requires a human-approved replacement")
    case["fulfillment"] = {
        "status": "stock_unavailable",
        "sandbox": True,
        "searched_pharmacy": "Northstar Community Pharmacy (synthetic)",
        "system_substitution": None,
    }
    case["status"] = "stock_escalated"
    _append(
        case,
        "Fulfillment agent",
        "Matching stock unavailable",
        "No product was substituted. An alternate matching-stock search requires confirmation.",
        status="attention",
        evidence_ids=["review-decision", "sandbox-stock-miss"],
    )
    return case


def resolve_matching_stock(case: dict[str, Any]) -> dict[str, Any]:
    if case["status"] != "stock_escalated":
        raise ValueError("alternate stock requires a recorded stock escalation")
    case["fulfillment"] = {"status": "not_started", "alternate_match_verified": True}
    case["status"] = "replacement_approved"
    _append(
        case,
        "Fulfillment agent",
        "Alternate matching stock verified",
        "A synthetic pharmacy confirmed the exact approved product; no substitution was inferred.",
        evidence_ids=["review-decision", "sandbox-alternate-stock"],
    )
    return case


def report_courier_unavailable(case: dict[str, Any]) -> dict[str, Any]:
    if case.get("fulfillment", {}).get("status") != "prepared":
        raise ValueError("delivery recovery requires prepared fulfillment")
    case["delivery"] = {
        "status": "courier_unavailable",
        "sandbox": True,
        "system_selected_alternative": None,
        "options": ["household pickup", "pharmacy-arranged accessible courier"],
    }
    case["status"] = "delivery_choice_required"
    _append(
        case,
        "Logistics agent",
        "Courier unavailable",
        "Two sandbox alternatives were surfaced; the system selected neither.",
        status="attention",
        evidence_ids=["sandbox-courier-failure"],
    )
    return case


def choose_accessible_courier(case: dict[str, Any], chosen_by: str) -> dict[str, Any]:
    if case["status"] != "delivery_choice_required" or len(chosen_by.strip()) < 3:
        raise ValueError("a named human must choose a delivery alternative")
    case["delivery"].update(
        {
            "status": "not_started",
            "selected_option": "pharmacy-arranged accessible courier",
            "selected_by": chosen_by.strip(),
            "selected_by_ai": False,
        }
    )
    case["status"] = "fulfillment_prepared"
    _append(
        case,
        "Household",
        "Accessible courier option selected",
        f"{chosen_by.strip()} selected the delivery recovery path; AI selected nothing.",
        evidence_ids=["sandbox-courier-failure", "human-delivery-choice"],
    )
    return case
