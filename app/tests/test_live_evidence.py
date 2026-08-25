from pathlib import Path
from types import SimpleNamespace

from cold_clock.live_evidence import LiveEvidenceRunner
from cold_clock.workflow import create_case


class Reader:
    def read(self, artifact, mime):
        return SimpleNamespace(transcription="NAME 100 units/mL vial Lot DEMO", fields=[
            {"key": "name", "value": "NAME", "quote": "NAME", "confidence": 1},
            {"key": "strength", "value": "100 units/mL", "quote": "100 units/mL", "confidence": 1},
            {"key": "form", "value": "vial", "quote": "vial", "confidence": 1},
        ], dropped=[])


class Router:
    def rank(self, query, candidates):
        return {"model": "gemini-embedding-001", "mode": "live-vertex-ai", "winner": "professional-review", "scores": {key: 0.5 for key in candidates}, "live": True}


def test_live_models_change_the_operational_record():
    web = Path(__file__).resolve().parents[1] / "web"
    class NoScreen:
        pass

    runner = LiveEvidenceRunner("test", web, Reader(), Router(), NoScreen())
    runner.screen_reviewer = None
    case = runner.apply(create_case())
    assert case["extraction"]["mode"] == "live-vertex-ai"
    assert case["semantic_routing"]["model"] == "gemini-embedding-001"
    assert case["timeline"][-2]["actor"] == "Live evidence agent"
    assert case["timeline"][-1]["actor"] == "Guardrail agent"
    assert case["injection_screen"]["mode"] == "pattern-only"
