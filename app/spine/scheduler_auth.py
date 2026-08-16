"""Verify Cloud Scheduler OIDC calls before dispatching durable wakes."""
from __future__ import annotations
import os
from google.auth.transport.requests import Request
from google.oauth2 import id_token
def verify_scheduler_token(authorization,verifier=None):
 audience=os.getenv("SCHEDULER_AUDIENCE","").strip();expected=os.getenv("SCHEDULER_SERVICE_ACCOUNT","").strip()
 if not audience or not expected:
  if os.getenv("USE_FIRESTORE","").lower() in {"1","true","yes"}:raise ValueError("scheduler identity is not configured")
  return {"mode":"local-test"}
 if not authorization or not authorization.startswith("Bearer "):raise ValueError("missing scheduler bearer token")
 verify=verifier or (lambda token,aud:id_token.verify_oauth2_token(token,Request(),audience=aud));claims=verify(authorization[7:],audience)
 if claims.get("email")!=expected or claims.get("email_verified") is not True:raise ValueError("scheduler identity rejected")
 if claims.get("iss") not in {"accounts.google.com","https://accounts.google.com"}:raise ValueError("scheduler issuer rejected")
 return {"mode":"google-oidc","email":expected}
