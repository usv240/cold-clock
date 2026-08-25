"""De-identified pilot intake and idempotent sensor-event handling.

This module turns the fixed public story into an input-driven coordination workspace without
crossing ColdClock's clinical boundary. Users provide the package facts, the authoritative label
excerpt, and the monitored range. ColdClock records excursions; it never decides disposition.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cold_clock.workflow import _append, create_case


def _utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamps must be ISO-8601 values") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def create_pilot_case(intake: dict[str, Any]) -> dict[str, Any]:
    """Create a case from authorized synthetic or de-identified pilot input."""

    transcript = str(intake["package_transcription"]).strip()
    medication = intake["medication"]
    exact_fields = {
        "name": str(medication["display_name"]).strip(),
        "strength": str(medication["strength"]).strip(),
        "form": str(medication["form"]).strip(),
        "lot": str(medication["lot"]).strip(),
    }
    missing = [key for key, value in exact_fields.items() if value not in transcript]
    if missing:
        raise ValueError("package transcription must contain each entered package field exactly: " + ", ".join(missing))

    low = float(intake["monitoring_range_f"]["minimum"])
    high = float(intake["monitoring_range_f"]["maximum"])
    baseline = float(intake["baseline_fahrenheit"])
    if low >= high:
        raise ValueError("monitoring range minimum must be below maximum")
    if not -40 <= low <= 130 or not -40 <= high <= 130 or not -40 <= baseline <= 160:
        raise ValueError("temperature values are outside the supported pilot range")

    case = create_case()
    created = datetime.now(timezone.utc)
    case.update(
        {
            "synthetic": intake["data_class"] == "synthetic",
            "origin": "pilot_input",
            "clock_mode": "realtime",
            "data_class": intake["data_class"],
            "created_at": _iso(created),
            "opened_at": _iso(created),
            "service_area": str(intake.get("service_area") or "grid-7").strip(),
            "household": {
                "display_name": str(intake["case_reference"]).strip(),
                "contact_preference": intake["contact_preference"],
                "mobility_note": str(intake.get("mobility_note") or "Not provided").strip(),
            },
            "medication": {
                "display_name": exact_fields["name"],
                "strength": exact_fields["strength"],
                "form": exact_fields["form"],
                "lot": exact_fields["lot"],
                "opened_on": str(medication.get("opened_on") or "Not provided").strip(),
                "package_is_synthetic": intake["data_class"] == "synthetic",
            },
            "extraction": {
                "model": None,
                "mode": "user-confirmed-verbatim",
                "transcription": transcript,
                "fields": [
                    {"key": key, "value": value, "quote": value, "verified": True, "provenance": "user-confirmed-verbatim"}
                    for key, value in {
                        "name": str(medication["display_name"]).strip(),
                        "strength": str(medication["strength"]).strip(),
                        "form": str(medication["form"]).strip(),
                        "lot": str(medication["lot"]).strip(),
                    }.items()
                ],
                "accuracy": {"matched": 4, "total": 4, "invented": 0},
            },
            "label_evidence": {
                "source_id": "user-authorized-label-source",
                "title": str(intake["label_source_title"]).strip(),
                "url": str(intake["label_source_url"]),
                "retrieved_on": created.date().isoformat(),
                "jurisdiction": str(intake["jurisdiction"]).strip(),
                "quoted_storage_text": str(intake["quoted_storage_text"]).strip(),
                "bounded_interpretation": "Observed readings are compared with the configured range; this does not determine medication disposition.",
                "source_verified_by_user": True,
            },
            "monitoring_range_f": {"minimum": low, "maximum": high, "configured_by": "authorized pilot user"},
            "sensor": {
                "source": str(intake["sensor_source"]).strip(),
                "state": "normal",
                "readings": [{"at": _iso(created), "fahrenheit": baseline, "power": "on"}],
                "processed_event_ids": [],
            },
            "timeline": [],
        }
    )
    _append(case, "Pilot intake", "Case enrolled from supplied evidence", "Four package fields were retained because each appears verbatim in the supplied transcription.", evidence_ids=["user-package-transcription", "user-authorized-label-source"])
    _append(case, "Monitor agent", "Monitoring active", f"{case['sensor']['source']} is reporting against the configured {low:g}–{high:g}°F range.", evidence_ids=["configured-monitoring-range"])
    return case


def ingest_sensor_event(case: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Ingest one normalized sensor event exactly once and detect, but never judge, an excursion."""

    event_id = str(event["event_id"]).strip()
    processed = case["sensor"].setdefault("processed_event_ids", [])
    if event_id in processed:
        case["last_ingestion"] = {"event_id": event_id, "duplicate": True}
        return case
    if case["status"] != "monitoring":
        raise ValueError("new sensor events can only be ingested while a case is monitoring")

    started = _utc(str(event["started_at"]))
    ended = _utc(str(event["ended_at"]))
    if ended <= started:
        raise ValueError("sensor event end must be after its start")
    minimum = float(event["minimum_fahrenheit"])
    maximum = float(event["maximum_fahrenheit"])
    latest = float(event["latest_fahrenheit"])
    if minimum > maximum or not minimum <= latest <= maximum:
        raise ValueError("sensor event temperatures are internally inconsistent")
    if any(value < -40 or value > 160 for value in (minimum, maximum, latest)):
        raise ValueError("sensor event temperatures are outside the supported pilot range")

    midpoint = started + (ended - started) / 2
    case["sensor"]["readings"].extend(
        [
            {"at": _iso(started), "fahrenheit": minimum, "power": event["power"]},
            {"at": _iso(midpoint), "fahrenheit": maximum, "power": event["power"]},
            {"at": _iso(ended), "fahrenheit": latest, "power": event["power"]},
        ]
    )
    processed.append(event_id)
    low = float(case.get("monitoring_range_f", {}).get("minimum", 36.0))
    high = float(case.get("monitoring_range_f", {}).get("maximum", 46.0))
    excursion = minimum < low or maximum > high
    case["last_ingestion"] = {"event_id": event_id, "duplicate": False, "excursion_detected": excursion}
    if not excursion:
        _append(case, "Sensor gateway", "In-range event ingested", f"Event {event_id} was recorded exactly once; no configured-range excursion was detected.", evidence_ids=[event_id])
        return case

    duration = round((ended - started).total_seconds() / 60)
    case["sensor"]["state"] = "excursion"
    case["excursion"] = {
        "source_event_id": event_id,
        "started_at": _iso(started),
        "ended_at": _iso(ended),
        "observed_minutes": duration,
        "minimum_fahrenheit": minimum,
        "maximum_fahrenheit": maximum,
        "power_event": event["power"],
        "assessment": "professional_review_required",
        "ai_disposition": None,
    }
    case["status"] = "excursion_detected"
    _append(case, "Sensor gateway", "Configured-range excursion recorded", f"Event {event_id} was ingested exactly once. Time and temperature were calculated; no medication decision was made.", status="attention", evidence_ids=[event_id, "configured-monitoring-range", case["label_evidence"]["source_id"]])
    return case
