"""Utility-outage fan-out: one grid event, every enrolled case, no operator.

A utility publishes one message: "grid-7 lost power at T". ColdClock does not wait for someone to
open each case. It marks every monitoring case in that service area, registers an ``outage_watch``
wake for each, and lets the background worker decide per case from evidence:

* out-of-range readings since the outage  -> excursion recorded, review packet routed;
* readings still in range                  -> keep watching (bounded rechecks);
* no readings at all during the outage     -> safe stop for incomplete evidence.

Nothing here decides what happens to the medicine.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from cold_clock.failures import report_sensor_gap
from cold_clock.workflow import _append, _iso, advance_safe_automation

DEFAULT_SERVICE_AREA = "grid-7"
OUTAGE_WATCH_MINUTES = 15
MAX_OUTAGE_RECHECKS = 3


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def service_area_of(case: dict[str, Any]) -> str:
    return str(case.get("service_area") or DEFAULT_SERVICE_AREA)


def apply_utility_outage(case: dict[str, Any], outage: dict[str, Any], *, channel: str = "api") -> bool:
    """Mark one monitoring case as affected. Returns False when the case is not eligible."""
    if case["status"] != "monitoring":
        return False
    outage_id = str(outage["outage_id"])
    existing = case.get("utility_outage") or {}
    if existing.get("outage_id") == outage_id:
        return False
    if existing and existing.get("resolution") is None:
        # Already under an active watch for an earlier outage; that watch will judge the case.
        return False
    started_at = _utc(outage["started_at"])
    latest = case["sensor"]["readings"][-1]
    readings_before = len(case["sensor"]["readings"])
    case["sensor"]["readings"].append({"at": _iso(started_at), "fahrenheit": latest.get("fahrenheit"), "power": "off", "source": "utility-event"})
    case["utility_outage"] = {
        "outage_id": outage_id,
        "service_area": str(outage.get("service_area") or service_area_of(case)),
        "started_at": _iso(started_at),
        "channel": channel,
        "rechecks": 0,
        "resolution": None,
        # Evidence is judged by arrival order, not by comparing timestamps from different clocks:
        # a baseline reading stamped a few milliseconds after the utility's started_at is still pre-outage.
        "readings_at_outage": readings_before,
    }
    case.setdefault("event_channels", []).append({"channel": channel, "kind": "utility_outage", "id": outage_id})
    _append(
        case,
        "Utility outage gateway",
        "Grid outage reported",
        f"Outage {outage_id} in {case['utility_outage']['service_area']} arrived via {channel}. A background watch will judge this case from its own readings.",
        status="attention",
        evidence_ids=[f"utility-{outage_id}"],
        at=started_at,
    )
    return True


def register_outage_watch(case: dict[str, Any], scheduler, attempt: int = 0) -> None:
    if scheduler is None:
        return
    wake = scheduler.sleep_for(case["case_id"], "outage_watch", timedelta(minutes=OUTAGE_WATCH_MINUTES), payload={"attempt": attempt}, discriminator=str(attempt))
    rows = case.setdefault("scheduled_wakes", [])
    if not any(row["wake_id"] == wake.wake_id for row in rows):
        rows.append({"wake_id": wake.wake_id, "kind": wake.kind, "due_at": wake.due_at.isoformat()})


def _range(case: dict[str, Any]) -> tuple[float, float]:
    configured = case.get("monitoring_range_f") or {}
    return float(configured.get("minimum", 36.0)), float(configured.get("maximum", 46.0))


def evaluate_outage_watch(case: dict[str, Any], now: datetime, wake_id: str, attempt: int) -> str:
    """Decide from evidence. Returns the outcome label and mutates the case accordingly."""
    outage = case.get("utility_outage") or {}
    if case["status"] != "monitoring" or not outage or outage.get("resolution"):
        return "no_longer_needed"
    started = _utc(outage["started_at"])
    low, high = _range(case)
    readings = case["sensor"]["readings"]
    if outage.get("readings_at_outage") is not None:
        arrived_after = readings[int(outage["readings_at_outage"]) + 1:]  # everything appended after the outage marker
    else:  # older cases without the marker count: fall back to timestamps
        arrived_after = [row for row in readings if row.get("at") and _utc(row["at"]) > started]
    since = [row for row in arrived_after if row.get("source") != "utility-event" and row.get("at") and row.get("fahrenheit") is not None]
    out_of_range = [row for row in since if float(row["fahrenheit"]) < low or float(row["fahrenheit"]) > high]
    if out_of_range:
        first = _utc(out_of_range[0]["at"])
        last = _utc(since[-1]["at"])
        values = [float(row["fahrenheit"]) for row in since]
        case["sensor"]["state"] = "excursion"
        case["excursion"] = {
            "source_event_id": f"outage-watch:{outage['outage_id']}",
            "started_at": _iso(first),
            "ended_at": _iso(last),
            "observed_minutes": max(1, round((last - first).total_seconds() / 60)),
            "minimum_fahrenheit": min(values),
            "maximum_fahrenheit": max(values),
            "power_event": f"utility outage {outage['outage_id']}",
            "assessment": "professional_review_required",
            "ai_disposition": None,
        }
        case["status"] = "excursion_detected"
        outage["resolution"] = "excursion_recorded"
        _append(
            case,
            "Background wake agent",
            "Outage watch recorded an excursion",
            f"{len(out_of_range)} reading(s) since the outage were outside {low:g}–{high:g}°F. Observed facts were recorded; no medication decision was made.",
            status="attention",
            evidence_ids=[wake_id, "sensor-readings", f"utility-{outage['outage_id']}"],
            at=now,
        )
        advance_safe_automation(case)
        return "excursion_recorded"
    if since:
        if attempt >= MAX_OUTAGE_RECHECKS:
            outage["resolution"] = "held_in_range"
            _append(case, "Background wake agent", "Outage watch closed in range", f"Readings stayed within {low:g}–{high:g}°F through {attempt} rechecks; monitoring continues normally.", evidence_ids=[wake_id, "sensor-readings"], at=now)
            return "held_in_range"
        outage["rechecks"] = attempt + 1
        _append(case, "Background wake agent", "Outage watch: still in range", f"Latest reading {since[-1]['fahrenheit']}°F is within range; re-checking in {OUTAGE_WATCH_MINUTES} minutes.", evidence_ids=[wake_id, "sensor-readings"], at=now)
        return "recheck"
    if attempt >= 1:
        outage["resolution"] = "sensor_silent"
        report_sensor_gap(case)
        case["timeline"][-1]["at"] = _iso(now)
        case["timeline"][-1]["evidence_ids"].append(wake_id)
        return "sensor_gap_safe_stop"
    outage["rechecks"] = attempt + 1
    _append(case, "Background wake agent", "Outage watch: no readings yet", "No sensor reading has arrived since the outage; waiting one more interval before a safe stop.", status="attention", evidence_ids=[wake_id], at=now)
    return "recheck"
