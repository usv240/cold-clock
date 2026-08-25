"""Per-network request caps for the public, keyless surface.

The judge UI must stay keyless, so abuse control is by network fingerprint rather than identity:
model-backed demo runs are capped tightly, case creation more loosely. The keyed /v1 API has its
own Firestore-backed quota and is unaffected.
"""
from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, Response


class NetworkRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 3600, label: str = "requests"):
        self.limit = limit
        self.window = window_seconds
        self.label = label
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, network: str) -> tuple[bool, int]:
        now = monotonic()
        bucket = self._hits[network]
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False, 0
        bucket.append(now)
        return True, self.limit - len(bucket)

    def guard(self, request: Request, response: Response) -> None:
        from spine.developer_access import client_network

        allowed, remaining = self.check(client_network(request))
        response.headers["X-Demo-Limit"] = str(self.limit)
        response.headers["X-Demo-Remaining"] = str(remaining)
        if not allowed:
            raise HTTPException(status_code=429, detail=f"limit of {self.limit} {self.label} per network per hour reached; the /v1 API with a developer key remains available")


MODEL_RUNS = NetworkRateLimiter(limit=30, label="model-backed demo runs")
CASE_CREATES = NetworkRateLimiter(limit=120, label="case creations")
