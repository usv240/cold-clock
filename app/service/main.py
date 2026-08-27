"""Cloud Run entry point for ColdClock."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from cold_clock.store import ConcurrentWriteError, FirestoreCaseStore, MemoryCaseStore
from cold_clock.live_evidence import LiveEvidenceRunner
from service.routes import build_router
from service.pilot_routes import build_pilot_router
from service.developer_routes import build_developer_router
from service.events_routes import build_events_router
from service.hardening_routes import build_hardening_router
from service.runtime import build_runtime
from service import worker_status
from service.scheduler_routes import build_scheduler_router
from spine.http_trace import install_http_tracing
from spine.developer_access import DeveloperAccessManager, FirestoreAccessStore, MemoryAccessStore, build_access_router

PROJECT=os.environ.get("GOOGLE_CLOUD_PROJECT","local")
USE_FIRESTORE=os.environ.get("USE_FIRESTORE","").lower() in {"1","true","yes"}
ALLOW_GLOBAL_RESET=os.environ.get("ALLOW_GLOBAL_RESET","").lower() in {"1","true","yes"}
ALLOW_DEIDENTIFIED=os.environ.get("ALLOW_DEIDENTIFIED_PILOT","").lower() in {"1","true","yes"}
ENABLE_LIVE_MODELS=os.environ.get("ENABLE_LIVE_MODELS","").lower() in {"1","true","yes"}
GOOGLE_SERVICES=[
 {"name":"Gemini 3.5 Flash on Vertex AI","role":"Live fail-closed grounded package extraction"},
 {"name":"Google Gen AI SDK","role":"Model access for extraction, routing and screening"},
 {"name":"Google ADK","role":"Review-packet agent with scoped read-only tools and a post-model verifier"},
 {"name":"Pub/Sub","role":"OIDC push ingress for sensor events and utility-outage fan-out"},
 {"name":"Gemini Embedding 001","role":"Semantic evidence routing; never authority decisions"},
 {"name":"Gemma 4 on Vertex AI","role":"Second-layer prompt-injection screen on untrusted package text"},
 {"name":"Cloud Run","role":"Public container service"},
 {"name":"Firestore","role":"Durable cases and transactional wake state"},
 {"name":"Cloud Scheduler","role":"Every-minute OIDC-authenticated wake scans that close dispatched cases at the courier ETA"},
 {"name":"Cloud Trace","role":"End-to-end request observability"},
 {"name":"Secret Manager","role":"HMAC pepper for API-key and network-fingerprint protection"},
]
if USE_FIRESTORE:
 from google.cloud import firestore
 firestore_client=firestore.Client(project=PROJECT)
 case_store=FirestoreCaseStore(firestore_client); persistence="firestore"
else:
 firestore_client=None
 case_store=MemoryCaseStore(); persistence="memory-local"
if USE_FIRESTORE and not os.environ.get("API_KEY_PEPPER"):
 raise RuntimeError("API_KEY_PEPPER must be provided by Secret Manager in deployed mode")
access_store=FirestoreAccessStore(firestore_client,"cold_clock") if USE_FIRESTORE else MemoryAccessStore()
access_manager=DeveloperAccessManager(access_store,"cold_clock","cc_live_",os.environ.get("API_KEY_PEPPER","local-development-only-pepper"))
clock,wake_scheduler=build_runtime(PROJECT,USE_FIRESTORE)
app=FastAPI(title="ColdClock",description="Event-to-resolution coordination for refrigerated medicine excursions.",version="0.3.0")
trace_status=install_http_tracing(app,PROJECT,"cold-clock")
model_runner=LiveEvidenceRunner(PROJECT,Path(__file__).resolve().parent.parent/"web") if ENABLE_LIVE_MODELS else None
if ENABLE_LIVE_MODELS:
 import cold_clock.workflow as _workflow
 from cold_clock.packet_agent import AdkPacketAgent
 _workflow.PACKET_AGENT=AdkPacketAgent(PROJECT)
 def _warm_agent_stack():
  # ADK pulls in the Vertex SDK on first use (~20 s cold); do it once at boot instead of on a judge's first click.
  try:
   import google.adk.agents,google.adk.runners  # noqa: F401
   from google import genai  # noqa: F401
  except Exception:  # noqa: BLE001 - warmup is best effort; the receipt reports any real failure
   pass
 import threading;threading.Thread(target=_warm_agent_stack,name="warm-agent-stack",daemon=True).start()
RECEIPT_PEPPER=os.environ.get("API_KEY_PEPPER","local-development-only-pepper")

@app.exception_handler(ConcurrentWriteError)
async def concurrent_write(_request: Request, exc: ConcurrentWriteError) -> JSONResponse:
 return JSONResponse(status_code=409,content={"error":{"code":"concurrent_write","message":str(exc),"record_id":exc.record_id,"expected_version":exc.expected,"actual_version":exc.actual,"retryable":True}})

app.include_router(build_router(case_store,wake_scheduler,allow_global_reset=ALLOW_GLOBAL_RESET,model_runner=model_runner,receipt_pepper=RECEIPT_PEPPER)); app.include_router(build_pilot_router(case_store,wake_scheduler,allow_deidentified=ALLOW_DEIDENTIFIED)); app.include_router(build_hardening_router(case_store,wake_scheduler,clock))
app.include_router(build_scheduler_router(case_store,wake_scheduler)); app.include_router(build_events_router(case_store,wake_scheduler))
app.include_router(build_access_router(access_manager,"ColdClock","/v1/cases"))
app.include_router(build_developer_router(case_store,access_manager,wake_scheduler,allow_deidentified=ALLOW_DEIDENTIFIED,model_runner=model_runner))
WEB=Path(__file__).resolve().parent.parent/"web"; app.mount("/static",StaticFiles(directory=WEB),name="static")

@app.get("/health")
def health()->dict[str,Any]:
 return {"ok":True,"project":"cold-clock","google_cloud_project":PROJECT,"persistence":persistence,"synthetic_demo":True,"operating_mode":"protected-deidentified-pilot" if ALLOW_DEIDENTIFIED else "public-synthetic-pilot","pilot_api":"/api/pilot","public_data_policy":"authorized-deidentified" if ALLOW_DEIDENTIFIED else "synthetic-only","global_reset":ALLOW_GLOBAL_RESET,"clinical_decisions":"human-only","model":"gemini-3.5-flash","models":["gemini-3.5-flash","gemini-embedding-001","gemma-4-26b-a4b-it-maas"],"model_mode":"live-fail-closed" if ENABLE_LIVE_MODELS else "local-test-no-model","tracing":trace_status,"durable_wakes":"firestore-transactional" if USE_FIRESTORE else "memory-transactional","frameworks":["Google Gen AI SDK","Google ADK"],"packet_agent":"adk-scoped-tools-verified" if ENABLE_LIVE_MODELS else "deterministic-local","event_ingress":{"sensor":"/internal/events/sensor","utility":"/internal/events/utility","transport":"Pub/Sub push with Google-signed OIDC"},"background_execution":{"worker":"/internal/wakes/scan","trigger":"Cloud Scheduler every minute, Google-signed OIDC","closes_cases":"courier_status_poll wake at sandbox ETA","outage_fanout":"outage_watch wakes per affected case","unattended_demo":"/api/demo/unattended"},"signed_receipts":"HMAC-SHA256, verify at POST /api/receipts/verify","background_worker":worker_status.snapshot(),"domain_state_writes":"transactional-optimistic-versioning","simulation_clock":True,"autonomy":"event-driven-safe-auto-continuation","developer_api":{"base":"/v1","key_issuance":"/api/developer/keys","daily_limit":50},"google_services":GOOGLE_SERVICES}
@app.middleware("http")
async def revalidate_static(request:Request,call_next):
 response=await call_next(request)
 if request.url.path=="/" or request.url.path.startswith("/static/"):
  response.headers["Cache-Control"]="no-cache"  # browsers revalidate so a deploy never serves a stale CSS/HTML mix
 return response
@app.get("/",include_in_schema=False)
def index()->FileResponse:return FileResponse(WEB/"index.html")
