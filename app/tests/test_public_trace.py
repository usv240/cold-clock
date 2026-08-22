from fastapi.testclient import TestClient

from service.main import app


def test_public_trace_is_useful_and_redacted():
    client = TestClient(app)
    case = client.post("/api/demo/full").json()
    trace = client.get(f'/api/cases/{case["case_id"]}/trace').json()
    assert trace["event_count"] == len(case["timeline"])
    assert trace["events"][0]["actor"]
    serialized = str(trace).lower()
    assert "raw prompts" in serialized
    assert "rationale" not in serialized and "mobility_note" not in serialized
