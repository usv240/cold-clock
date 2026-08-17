from cold_clock.pilot import create_pilot_case, ingest_sensor_event


def intake():
    return {
        "data_use_acknowledgement": True,
        "data_class": "synthetic",
        "case_reference": "Pilot case A-104",
        "contact_preference": "text",
        "mobility_note": "Accessible delivery requested",
        "medication": {"display_name": "Example biologic", "strength": "100 mg/mL", "form": "prefilled pen", "lot": "LOT-42", "opened_on": "2026-08-15"},
        "package_transcription": "Example biologic\n100 mg/mL\nprefilled pen\nLOT-42",
        "label_source_title": "Authorized package insert",
        "label_source_url": "https://example.test/label",
        "jurisdiction": "United States",
        "quoted_storage_text": "Store between 36 and 46 degrees Fahrenheit.",
        "monitoring_range_f": {"minimum": 36, "maximum": 46},
        "baseline_fahrenheit": 41,
        "sensor_source": "Pilot webhook sensor",
    }


def event(event_id="sensor-evt-1", maximum=73.0):
    return {"event_id": event_id, "started_at": "2026-08-16T10:00:00Z", "ended_at": "2026-08-16T11:30:00Z", "minimum_fahrenheit": 47.0, "maximum_fahrenheit": maximum, "latest_fahrenheit": 68.0, "power": "off"}


def test_pilot_case_uses_supplied_evidence_not_fixture():
    case = create_pilot_case(intake())
    assert case["origin"] == "pilot_input"
    assert len(case["case_id"]) > 30
    assert case["medication"]["display_name"] == "Example biologic"
    assert case["label_evidence"]["source_verified_by_user"] is True
    assert all(row["quote"] in case["extraction"]["transcription"] for row in case["extraction"]["fields"])


def test_sensor_event_is_dynamic_bounded_and_idempotent():
    case = create_pilot_case(intake())
    ingest_sensor_event(case, event())
    assert case["status"] == "excursion_detected"
    assert case["excursion"]["observed_minutes"] == 90
    assert case["excursion"]["maximum_fahrenheit"] == 73.0
    assert case["excursion"]["ai_disposition"] is None
    before = len(case["timeline"])
    case["status"] = "monitoring"
    ingest_sensor_event(case, event())
    assert len(case["timeline"]) == before
    assert case["last_ingestion"]["duplicate"] is True


def test_bad_transcription_and_bad_event_fail_closed():
    broken = intake()
    broken["package_transcription"] = "unrelated text"
    try:
        create_pilot_case(broken)
        assert False
    except ValueError as exc:
        assert "contain each entered" in str(exc)
    case = create_pilot_case(intake())
    invalid = event()
    invalid["ended_at"] = invalid["started_at"]
    try:
        ingest_sensor_event(case, invalid)
        assert False
    except ValueError as exc:
        assert "after its start" in str(exc)
