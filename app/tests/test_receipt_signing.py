from fastapi.testclient import TestClient

from service.main import app
from spine.receipt_signing import sign_receipt, verify_receipt

client = TestClient(app)


def test_signature_is_stable_and_detects_tampering():
    proof = {"record_id": "cc-1", "operator_continue_clicks": 0, "nested": {"b": 2, "a": 1}}
    signed = sign_receipt(proof, "pepper")
    assert verify_receipt(signed, "pepper") is True
    assert verify_receipt({**signed, "operator_continue_clicks": 3}, "pepper") is False
    assert verify_receipt(signed, "other-pepper") is False
    assert verify_receipt(proof, "pepper") is False
    assert sign_receipt(proof, "pepper")["signature"] == signed["signature"]


def test_autonomy_proof_endpoint_is_signed_and_verifiable():
    case = client.post("/api/demo/full").json()
    receipt = client.get(f"/api/cases/{case['case_id']}/autonomy-proof").json()
    assert receipt["signature"] and receipt["verify_endpoint"] == "POST /api/receipts/verify"
    assert client.post("/api/receipts/verify", json={"proof": receipt}).json()["valid"] is True
    tampered = {**receipt, "closed_by_background_wake": True}
    assert client.post("/api/receipts/verify", json={"proof": tampered}).json()["valid"] is False
