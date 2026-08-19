from pathlib import Path

from fastapi.testclient import TestClient

from service.main import app


client = TestClient(app)
WEB = Path(__file__).resolve().parents[1] / "web"


def test_health_exposes_truthful_google_service_inventory():
    services = {row["name"] for row in client.get("/health").json()["google_services"]}
    assert {"Gemini 3.5 Flash on Vertex AI", "Google Gen AI SDK", "Cloud Run", "Firestore", "Cloud Scheduler", "Cloud Trace"} <= services


def test_header_has_accessible_live_stack_control():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'id="cloud-status-trigger"' in html
    assert 'aria-expanded="false"' in html and 'aria-controls="cloud-status-panel"' in html
    assert 'id="cloud-status-panel"' in html and 'role="region"' in html
    assert "/static/cloud-status.css" in html and "/static/cloud-status.js" in html


def test_live_stack_controller_supports_pointer_keyboard_and_health():
    script = (WEB / "cloud-status.js").read_text(encoding="utf-8")
    assert all(token in script for token in ['mouseenter', 'focusin', 'Escape', 'requestJson("/health"'])
