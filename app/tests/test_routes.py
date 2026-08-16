from fastapi.testclient import TestClient

from service.main import app


client = TestClient(app)


def post(path, json=None):
    return client.post(path, json=json or {})


def test_health_and_public_pages():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["clinical_decisions"] == "human-only"
    assert client.get("/").status_code == 200
    assert client.get("/judges").status_code == 200


def test_http_flow_end_to_end():
    case = post("/api/cases").json()
    case_id = case["case_id"]
    assert post(f"/api/cases/{case_id}/fulfillment").status_code == 409
    case = post(f"/api/cases/{case_id}/outage").json()
    assert case["status"] == "excursion_detected"
    case = post(f"/api/cases/{case_id}/request-review").json()
    assert case["status"] == "awaiting_professional_review"
    case = post(
        f"/api/cases/{case_id}/review",
        {
            "disposition": "replace",
            "reviewer_name": "Avery Chen, PharmD - synthetic",
            "rationale": "Replacement approved in this synthetic tabletop case.",
        },
    ).json()
    assert case["review"]["decision"]["made_by_ai"] is False
    assert post(f"/api/cases/{case_id}/fulfillment").json()["status"] == "fulfillment_prepared"
    assert post(f"/api/cases/{case_id}/dispatch").json()["status"] == "delivery_dispatched"
    case = post(f"/api/cases/{case_id}/confirm-delivery").json()
    assert case["status"] == "resolved"
    assert client.get(f"/api/cases/{case_id}").json()["progress"]["resolution_complete"]


def test_proof_and_conformance_are_public_and_green():
    proof = client.get("/api/proof").json()
    assert proof["passed"] == proof["total"] == 8
    conformance = client.get("/api/conformance").json()
    assert conformance["category"] == "The Taskmaster"
    assert len(conformance["limitations"]) >= 4


def test_research_has_claim_boundary_and_source_classes():
    research = client.get("/api/research").json()
    assert "do not validate ColdClock" in research["claim_boundary"]
    assert len(research["sources"]) >= 6
    assert all(source["url"].startswith("https://") for source in research["sources"])
    assert all(source["class"] for source in research["sources"])


def test_no_route_claims_to_prescribe_or_decide_safety():
    paths = " ".join(app.openapi()["paths"])
    assert "/prescribe" not in paths
    assert "/safe" not in paths
    assert "/discard" not in paths
