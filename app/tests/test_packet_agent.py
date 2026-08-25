import json

from cold_clock.packet_agent import assemble_packet, build_tools, deterministic_packet, verify_packet
from cold_clock.workflow import create_case, request_review, trigger_outage
import cold_clock.workflow as workflow


def _case():
    case = create_case()
    trigger_outage(case)
    return case


class FakeAgent:
    model = "fake"

    def __init__(self, reply, calls=("get_verified_package_fields", "get_excursion_observation", "get_label_storage_excerpt")):
        self.reply = reply
        self.calls = list(calls)

    def run(self, case):
        return self.reply, self.calls


def test_tools_are_read_only_and_expose_only_observed_facts():
    case = _case()
    calls = []
    fields, excursion, label = build_tools(case, calls)
    assert set(fields()) == {"medicine", "package_fields_verified", "opened_on"}
    assert set(excursion()) == {"observed_minutes", "maximum_fahrenheit"}
    assert set(label()) == {"source_url", "quoted_storage_text"}
    assert calls == ["get_verified_package_fields", "get_excursion_observation", "get_label_storage_excerpt"]
    assert "disposition" not in json.dumps([fields(), excursion(), label()])


def test_faithful_agent_packet_is_accepted_and_its_question_used():
    case = _case()
    truth = deterministic_packet(case)
    reply = json.dumps({**truth, "question": "Which reviewed disposition should govern this synthetic case?"})
    packet, receipt = assemble_packet(case, FakeAgent(reply))
    assert receipt["accepted"] is True and receipt["live"] is True and receipt["framework"] == "google-adk"
    assert packet["question"].startswith("Which reviewed disposition")
    assert {key: packet[key] for key in truth if key != "question"} == {key: truth[key] for key in truth if key != "question"}


def test_invented_value_or_safety_claim_is_rejected_and_deterministic_packet_used():
    case = _case()
    truth = deterministic_packet(case)
    lie = json.dumps({**truth, "maximum_fahrenheit": 60.0, "question": "The insulin is safe to use, which disposition?"})
    packet, receipt = assemble_packet(case, FakeAgent(lie))
    assert packet == truth
    assert receipt["accepted"] is False
    assert set(receipt["rejected_fields"]) == {"maximum_fahrenheit", "question"}


def test_skipping_a_tool_is_rejected_even_if_values_match():
    case = _case()
    reply = json.dumps(deterministic_packet(case))
    packet, receipt = assemble_packet(case, FakeAgent(reply, calls=["get_excursion_observation"]))
    assert packet == deterministic_packet(case) and receipt["accepted"] is False
    assert "skipped" in receipt["reason"]


def test_agent_failure_is_visible_and_never_blocks_review():
    class Broken:
        model = "fake"

        def run(self, case):
            raise TimeoutError("model slow")

    case = _case()
    packet, receipt = assemble_packet(case, Broken())
    assert packet == deterministic_packet(case)
    assert receipt["live"] is False and receipt["reason"] == "TimeoutError"


def test_request_review_records_packet_agent_receipt_in_timeline(monkeypatch):
    case = _case()
    truth = deterministic_packet(case)
    monkeypatch.setattr(workflow, "PACKET_AGENT", FakeAgent(json.dumps(truth)))
    request_review(case)
    assert case["packet_agent"]["accepted"] is True
    assert "ADK review-packet agent called 3 scoped" in case["timeline"][-1]["detail"]
    assert "packet-agent-receipt" in case["timeline"][-1]["evidence_ids"]
    assert case["review"]["packet"]["maximum_fahrenheit"] == 95.2


def test_verify_packet_tolerates_numeric_types_but_not_values():
    truth = {"medicine": "X", "package_fields_verified": 5, "opened_on": "2026-08-12", "observed_minutes": 145, "maximum_fahrenheit": 95.2, "source_url": "u"}
    ok = {**truth, "package_fields_verified": 5.0, "question": "What reviewed disposition should govern this synthetic case?"}
    assert verify_packet(ok, truth) == []
    assert verify_packet({**ok, "observed_minutes": 144}, truth) == ["observed_minutes"]
