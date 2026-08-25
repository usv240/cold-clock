"""Live, fail-closed model evidence for the public synthetic workflow."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

from cold_clock.injection_screen import GemmaSpanReviewer, screen_package_text
from cold_clock.reader import PackageReader, VertexPackageClient
from spine.semantic_routing import VertexSemanticRouter


class LiveEvidenceRunner:
    def __init__(self, project: str, web_root: Path, reader=None, router=None, screen_reviewer=None):
        self.reader = reader or PackageReader(VertexPackageClient(project))
        self.router = router or VertexSemanticRouter(project)
        self.screen_reviewer = screen_reviewer or GemmaSpanReviewer(project)
        self.fixture = web_root / "package-fixture.png"

    def apply(self, case: dict[str, Any]) -> dict[str, Any]:
        artifact = self.fixture.read_bytes()
        started = perf_counter()
        result = self.reader.read(artifact, "image/png")
        if len(result.fields) < 3:
            raise RuntimeError("live package extraction retained fewer than three verified fields")
        by_key = {row["key"]: row["value"] for row in result.fields}
        mapping = {"name": "display_name", "strength": "strength", "form": "form", "lot": "lot", "opened_on": "opened_on"}
        for source, target in mapping.items():
            if source in by_key:
                case["medication"][target] = by_key[source]
        case["extraction"].update({
            "model": "gemini-3.5-flash",
            "mode": "live-vertex-ai",
            "transcription": result.transcription,
            "fields": result.fields,
            "accuracy": {"matched": len(result.fields), "total": len(result.fields) + len(result.dropped), "invented": 0},
        })
        screen = screen_package_text(result.transcription, self.screen_reviewer)
        case["injection_screen"] = {key: value for key, value in screen.items() if key != "quarantined_text"}
        route = self.router.rank(
            screen["quarantined_text"],
            {
                "label-storage-evidence": "manufacturer storage limits and temperature excursion evidence",
                "professional-review": "qualified pharmacist review of medicine disposition",
                "accessible-fulfillment": "replacement inventory and accessible delivery logistics",
            },
        )
        case["model_execution"] = {
            "live": True,
            "model": "gemini-3.5-flash",
            "artifact_sha256": sha256(artifact).hexdigest(),
            "verified_fields": len(result.fields),
            "dropped_fields": len(result.dropped),
            "latency_ms": round((perf_counter() - started) * 1000),
        }
        case["semantic_routing"] = route
        case["timeline"].append({
            "sequence": len(case["timeline"]) + 1,
            "at": case["created_at"],
            "actor": "Live evidence agent",
            "action": "Package evidence read and routed",
            "detail": "Gemini verified exact-quoted fields; the embedding model routed the evidence without making a medication decision.",
            "status": "complete",
            "evidence_ids": ["synthetic-package", route["winner"]],
        })
        case["timeline"].append({
            "sequence": len(case["timeline"]) + 1,
            "at": case["created_at"],
            "actor": "Guardrail agent",
            "action": "Package text screened for injected instructions" if screen["clean"] else "Instruction-shaped package text quarantined",
            "detail": (
                f"Pattern layer plus Gemma 4 found no instruction-shaped text in the transcription."
                if screen["clean"] and screen["live"]
                else f"{screen['quarantined_spans']} span(s) were quarantined before routing; nothing was followed."
                if not screen["clean"]
                else "Pattern layer found no instruction-shaped text; the Gemma layer was unavailable and is reported as such."
            ),
            "status": "complete" if screen["clean"] else "attention",
            "evidence_ids": ["synthetic-package", "injection-screen"],
        })
        return case
