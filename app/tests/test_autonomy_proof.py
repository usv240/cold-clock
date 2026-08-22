from fastapi.testclient import TestClient
from service.main import app

client = TestClient(app)


def test_cumulative_autonomy_proof_is_derived_and_publicly_inspectable():
    completed = client.post("/api/demo/full").json()
    proof = completed["autonomy_proof"]
    assert proof["derived_from_persisted_trace"] is True
    assert proof["automatic_trace_events"] > 0
    assert proof["human_authority_events"] > 0
    assert proof["operator_continue_clicks"] == 0
    assert proof["system_decisions_over_reserved_authority"] == 0
    assert proof["completion"] is True
    assert proof["synthetic_tabletop_completion"] is True
    receipt = client.get(f"/api/cases/{completed['case_id']}/autonomy-proof")
    assert receipt.status_code == 200
    assert receipt.json()["trace_events"] == len(completed["timeline"])

