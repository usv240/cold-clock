"""Publish a synthetic sensor or utility event to ColdClock's Pub/Sub topics.

    python scripts/publish_event.py utility --service-area grid-7
    python scripts/publish_event.py sensor --case-id cc-... --max 73 --latest 68

Uses Application Default Credentials and the Pub/Sub REST API, so no extra client library is
needed. The push subscription delivers the message to the OIDC-protected ingress on Cloud Run.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import google.auth
from google.auth.transport.requests import AuthorizedSession

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "agentic-fleet-2026")


def publish(topic: str, payload: dict) -> str:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/pubsub"])
    session = AuthorizedSession(credentials)
    body = {"messages": [{"data": base64.b64encode(json.dumps(payload).encode()).decode()}]}
    response = session.post(f"https://pubsub.googleapis.com/v1/projects/{PROJECT}/topics/{topic}:publish", json=body, timeout=30)
    response.raise_for_status()
    return response.json()["messageIds"][0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["utility", "sensor"])
    parser.add_argument("--service-area", default="grid-7")
    parser.add_argument("--case-id")
    parser.add_argument("--min", type=float, default=47.0)
    parser.add_argument("--max", type=float, default=73.0)
    parser.add_argument("--latest", type=float, default=68.0)
    parser.add_argument("--minutes", type=int, default=90)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    if args.kind == "utility":
        payload = {"outage_id": f"out-{uuid4().hex[:8]}", "service_area": args.service_area, "started_at": now.isoformat(), "power": "off"}
        message_id = publish("cold-clock-utility-events", payload)
    else:
        if not args.case_id:
            parser.error("--case-id is required for sensor events")
        payload = {
            "case_id": args.case_id,
            "event_id": f"evt-{uuid4().hex[:8]}",
            "started_at": (now - timedelta(minutes=args.minutes)).isoformat(),
            "ended_at": now.isoformat(),
            "minimum_fahrenheit": args.min,
            "maximum_fahrenheit": args.max,
            "latest_fahrenheit": args.latest,
            "power": "off",
        }
        message_id = publish("cold-clock-sensor-events", payload)
    print(json.dumps({"published": message_id, "payload": payload}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
