"""Cloud Run entry point for ColdClock."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from cold_clock.store import FirestoreCaseStore, MemoryCaseStore
from service.routes import build_router
from service.hardening_routes import build_hardening_router
from service.runtime import build_runtime
from service.scheduler_routes import build_scheduler_router
from spine.http_trace import install_http_tracing

PROJECT=os.environ.get("GOOGLE_CLOUD_PROJECT","local")
USE_FIRESTORE=os.environ.get("USE_FIRESTORE","").lower() in {"1","true","yes"}
if USE_FIRESTORE:
 from google.cloud import firestore
 case_store=FirestoreCaseStore(firestore.Client(project=PROJECT)); persistence="firestore"
else: case_store=MemoryCaseStore(); persistence="memory-local"
clock,wake_scheduler=build_runtime(PROJECT,USE_FIRESTORE)
app=FastAPI(title="ColdClock",description="Event-to-resolution coordination for refrigerated medicine excursions.",version="0.2.0")
trace_status=install_http_tracing(app,PROJECT,"cold-clock")
app.include_router(build_router(case_store)); app.include_router(build_hardening_router(case_store,wake_scheduler,clock))
app.include_router(build_scheduler_router(case_store,wake_scheduler))
WEB=Path(__file__).resolve().parent.parent/"web"; app.mount("/static",StaticFiles(directory=WEB),name="static")

@app.get("/health")
def health()->dict[str,Any]:
 return {"ok":True,"project":"cold-clock","google_cloud_project":PROJECT,"persistence":persistence,"synthetic_demo":True,"clinical_decisions":"human-only","model":"gemini-3.5-flash","model_mode":"live Vertex AI recording with deterministic replay","tracing":trace_status,"durable_wakes":"firestore-transactional" if USE_FIRESTORE else "memory-transactional","simulation_clock":True}
@app.get("/",include_in_schema=False)
def index()->FileResponse:return FileResponse(WEB/"index.html")
@app.get("/judges",include_in_schema=False)
def judges()->FileResponse:return FileResponse(WEB/"hardening.html")
@app.get("/judges/architecture",include_in_schema=False)
def architecture_brief()->FileResponse:return FileResponse(WEB/"judges.html")
