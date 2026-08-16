"""Executable ColdClock acceptance flow against local or deployed HTTP service."""

from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def call(base: str, method: str, path: str, body: dict | None = None):
    payload = json.dumps(body or {}).encode("utf-8") if method == "POST" else None
    request = Request(
        f"{base.rstrip('/')}{path}",
        data=payload,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=20) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    checks = []

    def check(name, condition):
        checks.append(bool(condition))
        print(f"{'PASS' if condition else 'FAIL'}  {name}")

    _, health = call(args.url, "GET", "/health")
    check("health identifies ColdClock", health["project"] == "cold-clock")
    check("health states human clinical authority", health["clinical_decisions"] == "human-only")
    _, case = call(args.url, "POST", "/api/cases")
    case_id = case["case_id"]
    check("synthetic case starts monitoring", case["synthetic"] and case["status"] == "monitoring")
    try:
        call(args.url, "POST", f"/api/cases/{case_id}/fulfillment")
        blocked = False
    except HTTPError as exc:
        blocked = exc.code == 409
    check("pre-approval fulfillment is blocked", blocked)
    _, case = call(args.url, "POST", f"/api/cases/{case_id}/outage")
    check("outage creates observed excursion", case["status"] == "excursion_detected")
    check("AI makes no disposition", case["excursion"]["ai_disposition"] is None)
    _, case = call(args.url, "POST", f"/api/cases/{case_id}/request-review")
    check("review waits for human", case["review"]["status"] == "pending_human")
    _, case = call(
        args.url,
        "POST",
        f"/api/cases/{case_id}/review",
        {
            "disposition": "replace",
            "reviewer_name": "Avery Chen, PharmD — synthetic",
            "rationale": "Replacement approved in this synthetic tabletop case.",
        },
    )
    check("named human approves replacement", not case["review"]["decision"]["made_by_ai"])
    _, case = call(args.url, "POST", f"/api/cases/{case_id}/fulfillment")
    check("sandbox inventory reserved after approval", case["fulfillment"]["sandbox"])
    _, case = call(args.url, "POST", f"/api/cases/{case_id}/dispatch")
    check("synthetic courier dispatched", case["delivery"]["status"] == "dispatched")
    _, case = call(args.url, "POST", f"/api/cases/{case_id}/confirm-delivery")
    check("receipt closes the workflow", case["status"] == "resolved")
    _, proof = call(args.url, "GET", "/api/proof")
    check("executable safety proof is green", proof["passed"] == proof["total"])
    print(f"\n{sum(checks)}/{len(checks)} checks passed")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

