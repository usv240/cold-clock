"""Live Vertex AI semantic evidence routing with an explicit, testable receipt."""
from __future__ import annotations

from math import sqrt
from time import perf_counter
from typing import Any


class SemanticRoutingError(RuntimeError):
    pass


class VertexSemanticRouter:
    model = "gemini-embedding-001"

    def __init__(self, project: str, location: str = "global"):
        self.project = project
        self.location = location

    def _embed(self, text: str) -> list[float]:
        from google import genai
        from google.genai.types import EmbedContentConfig

        client = genai.Client(vertexai=True, project=self.project, location=self.location)
        response = client.models.embed_content(
            model=self.model,
            contents=text[:8000],
            config=EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
                output_dimensionality=128,
            ),
        )
        values = list(response.embeddings[0].values)
        if not values:
            raise SemanticRoutingError("embedding model returned no values")
        return values

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            raise SemanticRoutingError("embedding vector has zero norm")
        return numerator / (left_norm * right_norm)

    def rank(self, query: str, candidates: dict[str, str]) -> dict[str, Any]:
        if not query.strip() or not candidates:
            raise ValueError("semantic routing requires a query and candidates")
        started = perf_counter()
        query_vector = self._embed(query)
        scores = {
            candidate_id: round(self._cosine(query_vector, self._embed(text)), 5)
            for candidate_id, text in candidates.items()
        }
        winner = max(scores, key=scores.get)
        return {
            "model": self.model,
            "mode": "live-vertex-ai",
            "purpose": "semantic evidence routing; never an authority decision",
            "winner": winner,
            "scores": scores,
            "latency_ms": round((perf_counter() - started) * 1000),
            "live": True,
        }

