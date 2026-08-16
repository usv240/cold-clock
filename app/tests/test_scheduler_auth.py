import pytest
from spine.scheduler_auth import verify_scheduler_token


def test_local_mode_is_explicit(monkeypatch):
    monkeypatch.delenv("USE_FIRESTORE",raising=False);monkeypatch.delenv("SCHEDULER_AUDIENCE",raising=False);monkeypatch.delenv("SCHEDULER_SERVICE_ACCOUNT",raising=False)
    assert verify_scheduler_token(None)=={"mode":"local-test"}


def test_cloud_mode_fails_if_identity_not_configured(monkeypatch):
    monkeypatch.setenv("USE_FIRESTORE","true");monkeypatch.delenv("SCHEDULER_AUDIENCE",raising=False);monkeypatch.delenv("SCHEDULER_SERVICE_ACCOUNT",raising=False)
    with pytest.raises(ValueError,match="not configured"):verify_scheduler_token(None)


def test_valid_google_oidc_identity(monkeypatch):
    monkeypatch.setenv("SCHEDULER_AUDIENCE","https://service.test");monkeypatch.setenv("SCHEDULER_SERVICE_ACCOUNT","scheduler@example.test")
    claims={"email":"scheduler@example.test","email_verified":True,"iss":"https://accounts.google.com"}
    result=verify_scheduler_token("Bearer token",lambda token,aud:claims)
    assert result=={"mode":"google-oidc","email":"scheduler@example.test"}


def test_wrong_email_is_rejected(monkeypatch):
    monkeypatch.setenv("SCHEDULER_AUDIENCE","https://service.test");monkeypatch.setenv("SCHEDULER_SERVICE_ACCOUNT","scheduler@example.test")
    with pytest.raises(ValueError,match="identity rejected"):verify_scheduler_token("Bearer token",lambda token,aud:{"email":"attacker@example.test","email_verified":True,"iss":"accounts.google.com"})


def test_wrong_issuer_is_rejected(monkeypatch):
    monkeypatch.setenv("SCHEDULER_AUDIENCE","https://service.test");monkeypatch.setenv("SCHEDULER_SERVICE_ACCOUNT","scheduler@example.test")
    with pytest.raises(ValueError,match="issuer rejected"):verify_scheduler_token("Bearer token",lambda token,aud:{"email":"scheduler@example.test","email_verified":True,"iss":"https://evil.test"})
