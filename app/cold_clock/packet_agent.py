"""ADK review-packet agent with scoped, read-only tools and a post-model verifier.

The agent (Google ADK ``LlmAgent`` on Gemini 3.5 Flash) may only see the case through three
tools, each of which returns observed facts and nothing else: the exact-quote-verified package
fields, the excursion observation, and the authoritative label excerpt. It assembles the packet a
pharmacist will read. Its output is then verified field by field against what the tools returned.
Any invented or altered value rejects the whole packet and the deterministic packet is used
instead, with the rejection recorded. The model never sees a disposition vocabulary and the
verifier refuses a question that asserts safety. The workflow therefore never depends on the
model being right — only on it being checkable.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from time import perf_counter
from typing import Any

FRAMEWORK = "google-adk"
MODEL = os.getenv("COLD_CLOCK_PACKET_MODEL", "gemini-3.5-flash")
PACKET_FIELDS = ("medicine", "package_fields_verified", "opened_on", "observed_minutes", "maximum_fahrenheit", "source_url")
FORBIDDEN_QUESTION_TERMS = ("is safe", "unsafe", "discard", "may be used", "can be used", "should be used", "still good")

INSTRUCTION = (
    "You are ColdClock's review-packet agent. A qualified pharmacist, not you, decides what happens "
    "to the medicine. Call get_verified_package_fields, get_excursion_observation, and "
    "get_label_storage_excerpt, then reply with JSON only: "
    '{"medicine": str, "package_fields_verified": int, "opened_on": str, "observed_minutes": int, '
    '"maximum_fahrenheit": number, "source_url": str, "question": str}. '
    "Copy every value exactly from the tool results. The question must ask which reviewed "
    "disposition should govern this synthetic case and must not state or imply whether the "
    "medicine is safe, usable, or should be discarded."
)


def deterministic_packet(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "medicine": case["medication"]["display_name"],
        "package_fields_verified": case["extraction"]["accuracy"]["matched"],
        "observed_minutes": case["excursion"]["observed_minutes"],
        "maximum_fahrenheit": case["excursion"]["maximum_fahrenheit"],
        "opened_on": case["medication"]["opened_on"],
        "source_url": case["label_evidence"]["url"],
        "question": "What reviewed disposition should govern this synthetic case?",
    }


def build_tools(case: dict[str, Any], calls: list[str]):
    """Read-only closures over one case. Nothing here can mutate state or reach the network."""

    def get_verified_package_fields() -> dict:
        """Exact-quote-verified package fields for this case: medicine, count of verified fields, opened date."""
        calls.append("get_verified_package_fields")
        return {
            "medicine": case["medication"]["display_name"],
            "package_fields_verified": case["extraction"]["accuracy"]["matched"],
            "opened_on": case["medication"]["opened_on"],
        }

    def get_excursion_observation() -> dict:
        """Observed excursion duration in minutes and maximum temperature in Fahrenheit. No disposition."""
        calls.append("get_excursion_observation")
        return {
            "observed_minutes": case["excursion"]["observed_minutes"],
            "maximum_fahrenheit": case["excursion"]["maximum_fahrenheit"],
        }

    def get_label_storage_excerpt() -> dict:
        """Authoritative label source URL and its quoted storage text."""
        calls.append("get_label_storage_excerpt")
        return {
            "source_url": case["label_evidence"]["url"],
            "quoted_storage_text": case["label_evidence"]["quoted_storage_text"],
        }

    return [get_verified_package_fields, get_excursion_observation, get_label_storage_excerpt]


def verify_packet(candidate: dict[str, Any], truth: dict[str, Any]) -> list[str]:
    """Return the names of fields the model got wrong. Empty means the packet is accepted."""
    rejected: list[str] = []
    for key in PACKET_FIELDS:
        expected = truth[key]
        actual = candidate.get(key)
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            if abs(float(expected) - float(actual)) > 1e-9:
                rejected.append(key)
        elif str(actual).strip() != str(expected).strip():
            rejected.append(key)
    question = str(candidate.get("question") or "").strip()
    if len(question) < 10 or "disposition" not in question.lower() or any(term in question.lower() for term in FORBIDDEN_QUESTION_TERMS):
        rejected.append("question")
    return rejected


def generation_config():
    """Deterministic, bounded generation. Kept minimal on purpose: the installed google-genai
    build on Cloud Run rejected ``ThinkingConfig(thinking_level=...)`` with a ValidationError, which
    silently downgraded every packet to the deterministic path until the receipt exposed it."""
    from google.genai import types

    return types.GenerateContentConfig(temperature=0, max_output_tokens=1024)


class AdkPacketAgent:
    """Runs one ADK turn with the scoped tools and returns raw text plus the tool-call order."""

    def __init__(self, project: str, location: str = "global", model: str = MODEL, timeout_seconds: int = 45):
        self.project = project
        self.location = location
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def _turn(self, case: dict[str, Any], calls: list[str]) -> str:
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", self.project)
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", self.location)
        from google.adk.agents import LlmAgent
        from google.adk.runners import InMemoryRunner
        from google.genai import types

        agent = LlmAgent(
            name="cold_clock_review_packet_agent",
            model=self.model,
            description="Assembles a pharmacist review packet from scoped read-only tools.",
            instruction=INSTRUCTION,
            tools=build_tools(case, calls),
            generate_content_config=generation_config(),
        )
        runner = InMemoryRunner(agent=agent, app_name="cold-clock")
        session = await runner.session_service.create_session(app_name="cold-clock", user_id="workflow")
        text = ""
        async for event in runner.run_async(
            user_id="workflow",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=f"Assemble the review packet for case {case['case_id']}.")]),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                text = "".join(part.text or "" for part in event.content.parts)
        return text

    def run(self, case: dict[str, Any]) -> tuple[str, list[str]]:
        calls: list[str] = []
        coroutine = asyncio.wait_for(self._turn(case, calls), timeout=self.timeout_seconds)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine), calls
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coroutine).result(timeout=self.timeout_seconds + 5), calls


def assemble_packet(case: dict[str, Any], agent: Any | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (packet, receipt). The packet is always safe to use; the receipt says who built it."""
    truth = deterministic_packet(case)
    if agent is None:
        return truth, {"framework": FRAMEWORK, "live": False, "mode": "deterministic", "accepted": False, "reason": "packet agent not configured"}
    started = perf_counter()
    try:
        raw, calls = agent.run(case)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        candidate = json.loads(match.group(0)) if match else {}
        rejected = verify_packet(candidate, truth)
        receipt = {
            "framework": FRAMEWORK,
            "model": getattr(agent, "model", MODEL),
            "live": True,
            "mode": "adk-scoped-tools",
            "tool_calls": calls,
            "tools_available": ["get_verified_package_fields", "get_excursion_observation", "get_label_storage_excerpt"],
            "verified_fields": [key for key in PACKET_FIELDS if key not in rejected],
            "rejected_fields": rejected,
            "accepted": not rejected and len(set(calls)) == 3,
            "latency_ms": round((perf_counter() - started) * 1000),
        }
        if not receipt["accepted"]:
            receipt["reason"] = "verifier rejected the model packet; deterministic packet used" if rejected else "agent skipped a required tool; deterministic packet used"
            return truth, receipt
        packet = {**truth, "question": str(candidate["question"]).strip()}
        return packet, receipt
    except Exception as exc:  # noqa: BLE001 - visible degradation, never a hidden failure
        return truth, {
            "framework": FRAMEWORK,
            "model": getattr(agent, "model", MODEL),
            "live": False,
            "mode": "deterministic-fallback",
            "accepted": False,
            "reason": f"{type(exc).__name__}",
            "latency_ms": round((perf_counter() - started) * 1000),
        }
