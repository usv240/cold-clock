from pathlib import Path

from fastapi.testclient import TestClient

from service.main import app


client = TestClient(app)


def test_one_request_demo_completes_full_server_side_workflow():
    case = client.post("/api/demo/full").json()
    assert case["status"] == "resolved"
    assert case["progress"]["resolution_complete"] is True
    assert case["review"]["decision"]["made_by_ai"] is False
    assert case["autonomy"]["complete"] is True
    assert len(case["timeline"]) == 8


def test_event_and_human_decision_auto_resume_safe_work():
    case = client.post("/api/cases").json()
    case = client.post(f"/api/cases/{case['case_id']}/outage").json()
    assert case["status"] == "awaiting_professional_review"
    assert case["autonomy"]["last_run_actions"] == ["review_packet_routed"]

    case = client.post(
        f"/api/cases/{case['case_id']}/review",
        json={
            "disposition": "replace",
            "reviewer_name": "Avery Chen, PharmD - synthetic",
            "rationale": "Replacement approved for this synthetic automation test.",
        },
    ).json()
    assert case["status"] == "delivery_dispatched"
    assert case["autonomy"]["last_run_actions"] == [
        "replacement_reserved",
        "accessible_delivery_dispatched",
    ]
    assert case["autonomy"]["current_wait"] == "courier_confirmation_wake_or_household_receipt"
    kinds = {row["kind"] for row in case["autonomy"]["pending_background_wakes"]}
    assert kinds == {"courier_status_poll", "receipt_followup"}


def test_autopilot_stops_without_inventing_external_evidence():
    case = client.post("/api/cases").json()
    resumed = client.post(f"/api/cases/{case['case_id']}/autopilot").json()
    assert resumed["status"] == "monitoring"
    assert resumed["autonomy"]["last_run_actions"] == []
    assert resumed["autonomy"]["current_wait"] == "sensor_event"

def test_primary_demo_is_one_server_request_with_distinct_receipt():
    web = Path(__file__).resolve().parents[1] / "web"
    html = (web / "index.html").read_text(encoding="utf-8")
    script = (web / "app.js").read_text(encoding="utf-8")
    css = (web / "autonomy.css").read_text(encoding="utf-8")
    assert 'id="autonomy-receipt"' in html and 'aria-live="polite"' in html
    assert "/static/autonomy.css" in html and "Complete synthetic tabletop" in html
    assert 'api("/api/demo/full"' in script
    assert "while (" not in script and "while(" not in script
    assert ".autonomy-rail" in css
    assert "renderAutonomy(caseData.autonomy, caseData.autonomy_proof)" in script

def test_ui_exposes_unattended_run_wake_panel_and_live_polling():
    web = Path(__file__).resolve().parents[1] / "web"
    html = (web / "index.html").read_text(encoding="utf-8")
    script = (web / "app.js").read_text(encoding="utf-8")
    css = (web / "autonomy.css").read_text(encoding="utf-8")
    assert 'id="unattended-demo"' in html and 'id="wake-list"' in html and 'id="advance-clock"' in html
    assert 'id="outage-fanout"' in html and 'id="packet-agent"' in html and 'api("/api/demo/outage-fanout"' in script
    assert 'id="autonomy-background"' in html and 'id="injection-screen"' in html
    assert 'api("/api/demo/unattended"' in script and "setInterval(pollActiveCase" in script
    assert "dispatch: false" in script, "the clock control must leave dispatch to Cloud Scheduler"
    assert ".wake-panel" in css and ".injection-screen" in css


def test_health_declares_autonomy_mode():
    assert client.get("/health").json()["autonomy"] == "event-driven-safe-auto-continuation"

def test_completed_demo_has_no_remaining_autonomy_wait():
    completed = client.post("/api/demo/full").json()
    assert completed["status"] == "resolved"
    assert completed["autonomy"]["complete"] is True
    assert completed["autonomy"]["current_wait"] is None
