from datetime import datetime, timezone
import pytest

from service.main import app
from spine.developer_access import DailyQuotaExceeded, DeveloperAccessManager, IssuanceLimitExceeded, MemoryAccessStore
from test_pilot import intake
from fastapi.testclient import TestClient


def test_key_is_one_time_hashed_and_quota_is_atomic():
    store = MemoryAccessStore()
    manager = DeveloperAccessManager(store, "test", "cc_live_", "test-pepper", now=lambda: datetime(2026, 8, 22, 12, tzinfo=timezone.utc))
    issued = manager.issue("203.0.113.7", "integration")
    assert issued["api_key"].startswith("cc_live_")
    assert issued["api_key"] not in repr(store.keys)
    assert "203.0.113.7" not in repr(store.issues)
    for index in range(2, 6):
        manager.issue("203.0.113.7", f"shared-network-{index}")
    with pytest.raises(IssuanceLimitExceeded):
        manager.issue("203.0.113.7", "sixth")
    for remaining in range(49, -1, -1):
        assert manager.consume(issued["api_key"], "203.0.113.7")["remaining"] == remaining
    with pytest.raises(DailyQuotaExceeded):
        manager.consume(issued["api_key"], "203.0.113.7")


def test_self_service_key_unlocks_real_v1_case_workflow():
    client = TestClient(app)
    assert client.post("/v1/cases", json=intake()).status_code == 401
    response = client.post("/api/developer/keys", json={"label": "pytest judge", "acceptable_use_acknowledgement": True})
    assert response.status_code == 201
    key = response.json()["api_key"]
    created = client.post("/v1/cases", json=intake(), headers={"X-API-Key": key})
    assert created.status_code == 201
    assert created.headers["X-RateLimit-Remaining"] == "49"
    assert created.json()["origin"] == "pilot_input"
    assert created.json()["autonomy_proof"]["derived_from_persisted_trace"] is True



def test_network_fingerprint_uses_trusted_proxy_tail_not_spoofed_prefix():
    from starlette.requests import Request
    from spine.developer_access import client_network

    request = Request({"type": "http", "headers": [(b"x-forwarded-for", b"198.51.100.99, 203.0.113.7")], "client": ("127.0.0.1", 5000)})
    assert client_network(request) == "203.0.113.7"
