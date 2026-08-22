from fastapi.testclient import TestClient
from service.main import app


def test_model_evidence_contract_is_public_and_honest():
    result = TestClient(app).get("/api/model-evidence").json()
    assert [row["name"] for row in result["models"]] == ["gemini-3.5-flash", "gemini-embedding-001"]
    assert "test-only" in result["replay_policy"]
