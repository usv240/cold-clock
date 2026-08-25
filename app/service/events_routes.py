"""Pub/Sub push ingress: sensor and utility events arrive asynchronously; nobody clicks.

Two push subscriptions deliver here with a Google-signed OIDC token for the dedicated worker
service account (the same verifier the Cloud Scheduler worker uses):

* ``cold-clock-sensor-events``  -> POST /internal/events/sensor   {case_id, event_id, started_at, ...}
* ``cold-clock-utility-events`` -> POST /internal/events/utility  {outage_id, service_area, started_at}

Malformed or unknown messages are acknowledged with a recorded reason so Pub/Sub does not redeliver
them forever; the rejection is the audit record. Everything downstream is the same durable
workflow the UI and the API use.
"""
from __future__ import annotations

import base64
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from cold_clock.followups import register_followups
from cold_clock.outage import apply_utility_outage, register_outage_watch, service_area_of
from cold_clock.pilot import ingest_sensor_event
from cold_clock.store import CaseStore
from cold_clock.workflow import advance_safe_automation
from service import worker_status
from spine.scheduler_auth import verify_scheduler_token


class PubSubMessage(BaseModel):
    data: str = Field(default="")
    messageId: str = Field(default="", max_length=120)
    attributes: dict[str, str] = Field(default_factory=dict)


class PubSubPush(BaseModel):
    message: PubSubMessage
    subscription: str = Field(default="", max_length=400)


SENSOR_KEYS = ("event_id", "started_at", "ended_at", "minimum_fahrenheit", "maximum_fahrenheit", "latest_fahrenheit", "power")


def fan_out_utility_outage(store: CaseStore, scheduler, outage: dict[str, Any], *, channel: str) -> dict[str, Any]:
    """Apply one outage to every monitoring case in its service area and arm a watch for each."""
    area = str(outage.get("service_area") or "")
    affected: list[str] = []
    skipped = 0
    for case in store.list_cases():
        if service_area_of(case) != area:
            continue
        if not apply_utility_outage(case, outage, channel=channel):
            skipped += 1
            continue
        register_outage_watch(case, scheduler, 0)
        store.put(case)
        affected.append(case["case_id"])
    return {"outage_id": str(outage["outage_id"]), "service_area": area, "affected_cases": affected, "skipped_cases": skipped}


def build_events_router(store: CaseStore, scheduler) -> APIRouter:
    router = APIRouter(prefix="/internal/events", tags=["event-ingress"])

    def decode(push: PubSubPush) -> dict[str, Any] | None:
        try:
            payload = json.loads(base64.b64decode(push.message.data or b"").decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def authenticate(authorization: str | None) -> dict[str, Any]:
        try:
            return verify_scheduler_token(authorization)
        except ValueError as exc:
            raise HTTPException(401, str(exc)) from exc

    @router.post("/sensor")
    def sensor_push(push: PubSubPush, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = authenticate(authorization)
        payload = decode(push)
        if payload is None:
            return {"ok": False, "accepted": True, "reason": "malformed message", "message_id": push.message.messageId}
        case_id = str(payload.get("case_id") or "")
        if not case_id or any(key not in payload for key in SENSOR_KEYS):
            return {"ok": False, "accepted": True, "reason": "unsupported event shape", "message_id": push.message.messageId}
        case = store.get(case_id)
        if case is None:
            return {"ok": False, "accepted": True, "reason": "unknown case", "message_id": push.message.messageId}
        try:
            ingest_sensor_event(case, {key: payload[key] for key in SENSOR_KEYS})
            advance_safe_automation(case)
            register_followups(case, scheduler)
        except ValueError as exc:
            return {"ok": False, "accepted": True, "reason": str(exc), "message_id": push.message.messageId}
        case.setdefault("event_channels", []).append({"channel": "pubsub", "kind": "sensor_event", "id": str(payload["event_id"])})
        store.put(case)
        worker_status.record_push("sensor_event")
        return {
            "ok": True,
            "identity": identity,
            "message_id": push.message.messageId,
            "case_id": case_id,
            "status": case["status"],
            "duplicate": bool((case.get("last_ingestion") or {}).get("duplicate")),
            "last_run_actions": (case.get("last_autonomy_run") or {}).get("actions", []),
        }

    @router.post("/utility")
    def utility_push(push: PubSubPush, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = authenticate(authorization)
        payload = decode(push)
        if payload is None:
            return {"ok": False, "accepted": True, "reason": "malformed message", "message_id": push.message.messageId}
        if not payload.get("outage_id") or not payload.get("service_area") or not payload.get("started_at"):
            return {"ok": False, "accepted": True, "reason": "unsupported event shape", "message_id": push.message.messageId}
        try:
            result = fan_out_utility_outage(store, scheduler, payload, channel="pubsub")
        except ValueError as exc:
            return {"ok": False, "accepted": True, "reason": str(exc), "message_id": push.message.messageId}
        worker_status.record_push("utility_outage")
        return {"ok": True, "identity": identity, "message_id": push.message.messageId, **result}

    return router
