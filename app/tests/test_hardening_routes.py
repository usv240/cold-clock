from fastapi.testclient import TestClient

from service.main import app


client = TestClient(app)


def create_case():
    response = client.post("/api/cases")
    assert response.status_code == 200
    return response.json()["case_id"]


def test_failure_lab_routes_and_recovery():
    case_id = create_case()
    assert client.post(f"/api/hardening/cases/{case_id}/sensor-gap").json()["status"] == "evidence_incomplete"


def test_review_wake_is_durable_and_idempotent():
    case_id = create_case()
    assert client.post(f"/api/cases/{case_id}/outage").status_code == 200
    wakes = client.get(f"/api/hardening/cases/{case_id}/wakes").json()["wakes"]
    assert len(wakes) == 1
    assert wakes[0]["kind"] == "review_followup"
    client.post("/api/hardening/advance", json={"minutes": 31})
    wakes = client.get(f"/api/hardening/cases/{case_id}/wakes").json()["wakes"]
    assert wakes[0]["status"] == "done"


def test_failure_lab_proof_is_all_green():
    result = client.get("/api/hardening/proof")
    assert result.status_code == 200
    body = result.json()
    assert body["passed"] == body["total"] == 17


def test_trace_headers_are_present():
    response = client.get("/health")
    assert response.headers["x-agent-trace-id"]
    assert response.headers["x-agent-trace-mode"] in {"local", "cloud-trace"}


def test_missing_case_is_explicit():
    response = client.post("/api/hardening/cases/cc-missing/sensor-gap")
    assert response.status_code == 404
    assert "no ColdClock case" in response.json()["detail"]

