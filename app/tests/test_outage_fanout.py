"""One grid outage, every enrolled case, judged individually by background wakes."""
import base64
import json
from datetime import timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cold_clock.outage import apply_utility_outage
from cold_clock.store import MemoryCaseStore
from cold_clock.wake_actions import ColdClockWakeExecutor
from cold_clock.workflow import create_case
from service.events_routes import build_events_router, fan_out_utility_outage
from service.main import app
from spine.clock import MemoryClockStateStore, SimulatedClock
from spine.wake import MemoryWakeStore, WakeScheduler

client = TestClient(app)


def _runtime():
    clock = SimulatedClock(MemoryClockStateStore())
    return clock, WakeScheduler(MemoryWakeStore(), clock), MemoryCaseStore()


def _reading(case, clock, minutes, fahrenheit):
    case["sensor"]["readings"].append({"at": (clock.now() + timedelta(minutes=minutes)).isoformat(), "fahrenheit": fahrenheit, "power": "off"})


def test_fanout_targets_only_monitoring_cases_in_the_area_and_is_idempotent():
    clock, scheduler, cases = _runtime()
    a, b, elsewhere = create_case(), create_case(), create_case()
    elsewhere["service_area"] = "grid-9"
    for row in (a, b, elsewhere):
        cases.put(row)
    outage = {"outage_id": "out-1", "service_area": "grid-7", "started_at": clock.now().isoformat()}
    first = fan_out_utility_outage(cases, scheduler, outage, channel="pubsub")
    assert set(first["affected_cases"]) == {a["case_id"], b["case_id"]}
    assert cases.get(a["case_id"])["utility_outage"]["channel"] == "pubsub"
    assert [row.kind for row in scheduler._store.for_run(a["case_id"])] == ["outage_watch"]
    again = fan_out_utility_outage(cases, scheduler, outage, channel="pubsub")
    assert again["affected_cases"] == [] and again["skipped_cases"] == 2
    assert len(cases.get(a["case_id"])["timeline"]) == 3


def test_outage_watch_judges_each_case_from_its_own_evidence():
    clock, scheduler, cases = _runtime()
    hot, cool, silent = create_case(), create_case(), create_case()
    for row in (hot, cool, silent):
        cases.put(row)
    fan_out_utility_outage(cases, scheduler, {"outage_id": "out-2", "service_area": "grid-7", "started_at": clock.now().isoformat()}, channel="api")
    hot_case, cool_case = cases.get(hot["case_id"]), cases.get(cool["case_id"])
    _reading(hot_case, clock, 5, 52.0); _reading(hot_case, clock, 10, 71.5); cases.put(hot_case)
    _reading(cool_case, clock, 8, 40.5); cases.put(cool_case)
    executor = ColdClockWakeExecutor(cases, clock, scheduler)

    clock.advance(timedelta(minutes=16))
    fired = scheduler.dispatch_due(executor.execute)
    assert len(fired) == 3
    hot_after = cases.get(hot["case_id"])
    assert hot_after["status"] == "awaiting_professional_review"
    assert hot_after["excursion"]["maximum_fahrenheit"] == 71.5 and hot_after["excursion"]["ai_disposition"] is None
    assert hot_after["autonomy"]["last_run_actions"] == ["review_packet_routed"] if "autonomy" in hot_after else hot_after["last_autonomy_run"]["actions"] == ["review_packet_routed"]
    assert {row.kind for row in scheduler.pending_for(hot["case_id"])} == {"review_followup"}
    cool_after = cases.get(cool["case_id"])
    assert cool_after["status"] == "monitoring" and cool_after["utility_outage"]["rechecks"] == 1
    assert scheduler.pending_for(cool["case_id"])[0].kind == "outage_watch"
    silent_after = cases.get(silent["case_id"])
    assert silent_after["status"] == "monitoring" and silent_after["timeline"][-1]["action"] == "Outage watch: no readings yet"

    clock.advance(timedelta(minutes=16))
    scheduler.dispatch_due(executor.execute)
    silent_after = cases.get(silent["case_id"])
    assert silent_after["status"] == "evidence_incomplete" and silent_after["safe_stop"]["system_disposition"] is None
    assert silent_after["utility_outage"]["resolution"] == "sensor_silent"
    cool_after = cases.get(cool["case_id"])
    assert cool_after["status"] == "monitoring" and cool_after["utility_outage"]["rechecks"] == 2

    for _ in range(3):
        clock.advance(timedelta(minutes=16))
        scheduler.dispatch_due(executor.execute)
    cool_final = cases.get(cool["case_id"])
    assert cool_final["utility_outage"]["resolution"] == "held_in_range" and cool_final["status"] == "monitoring"
    assert scheduler.pending_for(cool["case_id"]) == []
    for case_id in (hot["case_id"], cool["case_id"], silent["case_id"]):
        from cold_clock.workflow import public_view
        proof = public_view(cases.get(case_id))["autonomy_proof"]
        assert proof["unclassified_trace_events"] == 0 and proof["operator_continue_clicks"] == 0


def test_a_second_outage_is_not_stacked_on_an_active_watch():
    clock, scheduler, cases = _runtime()
    case = create_case(); cases.put(case)
    first = fan_out_utility_outage(cases, scheduler, {"outage_id": "out-a", "service_area": "grid-7", "started_at": clock.now().isoformat()}, channel="api")
    second = fan_out_utility_outage(cases, scheduler, {"outage_id": "out-b", "service_area": "grid-7", "started_at": clock.now().isoformat()}, channel="api")
    assert first["affected_cases"] == [case["case_id"]] and second["affected_cases"] == [] and second["skipped_cases"] == 1
    assert cases.get(case["case_id"])["utility_outage"]["outage_id"] == "out-a"
    assert len(scheduler._store.for_run(case["case_id"])) == 1


def test_apply_outage_ignores_cases_that_are_not_monitoring():
    case = create_case()
    case["status"] = "resolved"
    assert apply_utility_outage(case, {"outage_id": "o", "service_area": "grid-7", "started_at": "2026-08-25T10:00:00Z"}) is False


def _push(body):
    return {"message": {"data": base64.b64encode(json.dumps(body).encode()).decode(), "messageId": "m1"}, "subscription": "projects/test/subscriptions/push"}


def test_pubsub_push_ingress_applies_events_and_acks_bad_messages():
    clock, scheduler, cases = _runtime()
    case = create_case(); cases.put(case)
    push_app = FastAPI(); push_app.include_router(build_events_router(cases, scheduler)); push = TestClient(push_app)

    utility = push.post("/internal/events/utility", json=_push({"outage_id": "out-p", "service_area": "grid-7", "started_at": clock.now().isoformat()}))
    assert utility.status_code == 200 and utility.json()["ok"] is True and utility.json()["affected_cases"] == [case["case_id"]]

    sensor = push.post("/internal/events/sensor", json=_push({"case_id": case["case_id"], "event_id": "evt-1", "started_at": "2026-08-25T10:00:00Z", "ended_at": "2026-08-25T11:30:00Z", "minimum_fahrenheit": 47, "maximum_fahrenheit": 73, "latest_fahrenheit": 68, "power": "off"}))
    assert sensor.status_code == 200 and sensor.json()["status"] == "awaiting_professional_review"
    assert cases.get(case["case_id"])["event_channels"][-1] == {"channel": "pubsub", "kind": "sensor_event", "id": "evt-1"}
    duplicate = push.post("/internal/events/sensor", json=_push({"case_id": case["case_id"], "event_id": "evt-1", "started_at": "2026-08-25T10:00:00Z", "ended_at": "2026-08-25T11:30:00Z", "minimum_fahrenheit": 47, "maximum_fahrenheit": 73, "latest_fahrenheit": 68, "power": "off"}))
    assert duplicate.json()["duplicate"] is True

    bad = push.post("/internal/events/utility", json={"message": {"data": base64.b64encode(b"not json").decode(), "messageId": "m2"}})
    assert bad.status_code == 200 and bad.json() == {"ok": False, "accepted": True, "reason": "malformed message", "message_id": "m2"}
    unknown = push.post("/internal/events/sensor", json=_push({"case_id": "cc-nope", "event_id": "e", "started_at": "x", "ended_at": "y", "minimum_fahrenheit": 1, "maximum_fahrenheit": 2, "latest_fahrenheit": 1, "power": "off"}))
    assert unknown.json()["reason"] == "unknown case"


def test_http_outage_fanout_demo_enrolls_and_arms_watches():
    result = client.post("/api/demo/outage-fanout", json={"service_area": "grid-test", "enroll": 2}).json()
    assert len(result["enrolled"]) == 2 and set(result["affected_cases"]) == set(result["enrolled"])
    wakes = client.get(f"/api/cases/{result['enrolled'][0]}/wakes").json()["wakes"]
    assert [row["kind"] for row in wakes] == ["outage_watch"]
    case = client.get(f"/api/cases/{result['enrolled'][0]}").json()
    assert case["utility_outage"]["channel"] == "api" and case["timeline"][-1]["actor"] == "Utility outage gateway"
    assert case["autonomy_proof"]["external_evidence_events"] >= 1


def test_baseline_reading_stamped_after_outage_start_is_not_evidence():
    """Clock skew: a pre-outage baseline can carry a later timestamp than the utility's started_at."""
    clock, scheduler, cases = _runtime()
    case = create_case()
    case["sensor"]["readings"][-1]["at"] = (clock.now() + timedelta(seconds=2)).isoformat()  # baseline "after" the outage by the clock
    cases.put(case)
    fan_out_utility_outage(cases, scheduler, {"outage_id": "out-skew", "service_area": "grid-7", "started_at": clock.now().isoformat()}, channel="pubsub")
    executor = ColdClockWakeExecutor(cases, clock, scheduler)
    clock.advance(timedelta(minutes=16)); scheduler.dispatch_due(executor.execute)
    first = cases.get(case["case_id"])
    assert first["timeline"][-1]["action"] == "Outage watch: no readings yet", "the baseline must not count as a post-outage reading"
    clock.advance(timedelta(minutes=16)); scheduler.dispatch_due(executor.execute)
    assert cases.get(case["case_id"])["status"] == "evidence_incomplete"
