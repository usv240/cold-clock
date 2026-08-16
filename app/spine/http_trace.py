"""FastAPI request tracing backed by the shared OpenTelemetry primitive."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request

from spine.obs import SPAN_RUN, current_trace_id, setup_tracing, span


def install_http_tracing(app: FastAPI, project_id: str, service_name: str) -> dict[str, Any]:
    enabled = os.environ.get("ENABLE_CLOUD_TRACE", "").lower() in {"1", "true", "yes"}
    active = setup_tracing(project_id, service_name) if enabled else False

    @app.middleware("http")
    async def traced_request(request: Request, call_next):
        with span(
            SPAN_RUN,
            request.url.path.strip("/") or "landing",
            **{
                "http.request.method": request.method,
                "url.path": request.url.path,
                "service.name": service_name,
            },
        ):
            response = await call_next(request)
            response.headers["X-Agent-Trace-Id"] = current_trace_id() or "local-no-export"
            response.headers["X-Agent-Trace-Mode"] = "cloud-trace" if active else "local"
            return response

    return {"requested": enabled, "active": active, "service": service_name}

