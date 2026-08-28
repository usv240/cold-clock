"""Judge-facing proof surfaces: worker status, honest unattended mode, and demo throttling."""
from fastapi.testclient import TestClient

from service import worker_status
from service.main import app
from service.routes import DemoRateLimiter

client = TestClient(app)


def test_background_status_reports_scheduler_scans_and_pushes():
    before = client.get("/api/background/status").json()["scans"]
    scan = client.post("/internal/wakes/scan").json()
    assert scan["ok"] is True
    status = client.get("/api/background/status").json()
    assert status["scans"] == before + 1
    assert status["last_identity"] == {"mode": "local-test"}
    assert status["seconds_since_last_scan"] is not None and status["seconds_since_last_scan"] <= 5
    assert status["expected_scan_interval_seconds"] == 60
    assert client.get("/health").json()["background_worker"]["scans"] >= before + 1


def test_unattended_can_stop_at_the_real_human_gate():
    case = client.post("/api/demo/unattended", json={"stop_at_review": True}).json()
    assert case["status"] == "awaiting_professional_review"
    assert case["review"]["decision"] is None
    assert case["demo_completion_mode"] == "awaiting_real_review_then_background"
    assert case["delivery_eta_minutes"] == 0, "on-camera path polls the courier on the next scheduler tick"
    kinds = {row["kind"] for row in case["autonomy"]["pending_background_wakes"]}
    assert kinds == {"review_followup"}
    decided = client.post(f"/api/cases/{case['case_id']}/review", json={"disposition": "replace", "reviewer_name": "Avery Chen, PharmD - synthetic", "rationale": "Replacement approved after a real review in this test."}).json()
    assert decided["status"] == "delivery_dispatched"
    assert decided["delivery"]["eta_minutes"] == 0
    assert {row["kind"] for row in decided["autonomy"]["pending_background_wakes"]} == {"courier_status_poll", "receipt_followup"}


def test_default_unattended_still_runs_to_dispatch():
    case = client.post("/api/demo/unattended").json()
    assert case["status"] == "delivery_dispatched" and case["demo_completion_mode"] == "background_wake_pending"


def test_demo_rate_limiter_is_per_network_and_windowed():
    limiter = DemoRateLimiter(limit=2, window_seconds=3600)
    assert limiter.check("net-a") == (True, 1)
    assert limiter.check("net-a") == (True, 0)
    assert limiter.check("net-a") == (False, 0)
    assert limiter.check("net-b") == (True, 1)


def test_demo_endpoints_expose_remaining_budget_header():
    response = client.post("/api/demo/full")
    assert response.status_code == 200
    assert response.headers["X-Demo-Limit"] == "30"
    assert int(response.headers["X-Demo-Remaining"]) < 30


def test_ui_shows_scheduler_status_and_stops_at_real_review():
    from pathlib import Path

    web = Path(__file__).resolve().parents[1] / "web"
    html = (web / "index.html").read_text(encoding="utf-8")
    script = (web / "app.js").read_text(encoding="utf-8")
    assert 'id="worker-status"' in html
    assert 'api("/api/background/status")' in script
    assert "stop_at_review: true" in script


def test_init_never_calls_foreach_on_a_single_element_selector():
    """A `$(...).forEach` throws at load and silently disables every listener wired after it."""
    import re
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    assert not re.search(r"(?<!\$)\$\((['\"])[^'\"]+\1\)\.forEach", script)
