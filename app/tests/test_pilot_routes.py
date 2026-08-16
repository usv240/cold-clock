from fastapi.testclient import TestClient

from service.main import app


client = TestClient(app)


def payload(reference="Pilot case A-104"):
    return {
        "data_class": "synthetic",
        "case_reference": reference,
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


def test_pilot_api_creates_lists_and_ingests_real_event_shape():
    created = client.post("/api/pilot/cases", json=payload()).json()
    case_id = created["case_id"]
    listing = client.get("/api/pilot/cases").json()
    assert listing["count"] >= 1
    assert any(row["case_reference"] == "Pilot case A-104" for row in listing["cases"])
    event = {
        "event_id": "device-evt-9001",
        "started_at": "2026-08-16T10:00:00Z",
        "ended_at": "2026-08-16T11:30:00Z",
        "minimum_fahrenheit": 47,
        "maximum_fahrenheit": 73,
        "latest_fahrenheit": 68,
        "power": "off",
    }
    updated = client.post(f"/api/pilot/cases/{case_id}/sensor-events", json=event).json()
    assert updated["status"] == "excursion_detected"
    assert updated["excursion"]["source_event_id"] == "device-evt-9001"
    assert updated["excursion"]["ai_disposition"] is None
    duplicate = client.post(f"/api/pilot/cases/{case_id}/sensor-events", json=event).json()
    assert duplicate["last_ingestion"] == {"event_id": "device-evt-9001", "duplicate": True}
    assert len(duplicate["timeline"]) == len(updated["timeline"])


def test_pilot_readiness_is_honest_about_nonproduction_boundaries():
    readiness = client.get("/api/pilot/readiness").json()
    assert readiness["level"] == "public synthetic operational pilot"
    assert "not represented as production clinical software" in readiness["claim"]
    assert "customer-specific identity and tenant isolation" in readiness["required_before_phi_or_clinical_use"]
    assert readiness["public_data_policy"] == "synthetic-only"


def test_public_service_rejects_deidentified_intake_and_global_reset():
    protected = payload("Authorized de-identified case")
    protected["data_class"] = "deidentified-authorized"
    assert client.post("/api/pilot/cases", json=protected).status_code == 403
    assert client.post("/api/reset").status_code == 403
