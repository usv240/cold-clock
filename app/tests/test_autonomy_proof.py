from fastapi.testclient import TestClient
from service.main import app
from spine.autonomy_proof import build_autonomy_proof

client = TestClient(app)


def test_cumulative_autonomy_proof_is_derived_and_publicly_inspectable():
    completed = client.post("/api/demo/full").json()
    proof = completed["autonomy_proof"]
    assert proof["derived_from_persisted_trace"] is True
    assert proof["automatic_trace_events"] > 0
    assert proof["human_authority_events"] > 0
    assert proof["operator_continue_clicks"] == 0
    assert proof["unclassified_trace_events"] == 0
    assert proof["proof_integrity"] == "verified"
    assert proof["system_decisions_over_reserved_authority"] == 0
    assert proof["completion"] is True
    assert proof["synthetic_tabletop_completion"] is True
    receipt = client.get(f"/api/cases/{completed['case_id']}/autonomy-proof")
    assert receipt.status_code == 200
    assert receipt.json()["trace_events"] == len(completed["timeline"])


def test_autonomy_proof_fails_closed_for_unknown_actors_and_derives_continue_clicks():
    proof = build_autonomy_proof(
        {
            "case_id": "cc-proof",
            "status": "resolved",
            "timeline": [{"sequence": 1, "actor": "mystery worker", "action": "changed state"}],
            "operator_interactions": [{"action": "continue_clicked"}],
        },
        id_field="case_id",
        automatic_actors=("agent",),
        authority_actors=("reviewer",),
        external_actors=("sensor",),
    )
    assert proof["automatic_trace_events"] == 0
    assert proof["unclassified_trace_events"] == 1
    assert proof["operator_continue_clicks"] == 1
    assert proof["proof_integrity"] == "incomplete"
