"""The workflow must finish without anyone at a screen: the scheduler wake closes the case."""

from datetime import timedelta

from fastapi.testclient import TestClient

from cold_clock.followups import register_followups
from cold_clock.store import MemoryCaseStore
from cold_clock.wake_actions import ColdClockWakeExecutor
from cold_clock.workflow import create_case, public_view, run_unattended_demo
from service.main import app
from spine.clock import MemoryClockStateStore, SimulatedClock
from spine.wake import MemoryWakeStore, WakeScheduler, WakeStatus

client = TestClient(app)


def _runtime():
    clock = SimulatedClock(MemoryClockStateStore())
    scheduler = WakeScheduler(MemoryWakeStore(), clock)
    return clock, scheduler, MemoryCaseStore()


def test_unattended_run_never_fabricates_the_receipt_inside_the_request():
    case = run_unattended_demo(create_case(), courier_eta_minutes=1)
    assert case["status"] == "delivery_dispatched"
    assert case["delivery"]["eta_minutes"] == 1
    assert "received_at" not in case["delivery"]
    assert case["demo_completion_mode"] == "background_wake_pending"


def test_courier_poll_wake_closes_case_and_cancels_the_rest():
    clock, scheduler, cases = _runtime()
    case = run_unattended_demo(create_case(), courier_eta_minutes=1)
    assert register_followups(case, scheduler) == ["courier_status_poll", "receipt_followup"]
    cases.put(case)
    executor = ColdClockWakeExecutor(cases, clock, scheduler)

    assert scheduler.dispatch_due(executor.execute) == [], "must not fire before the ETA"
    clock.advance(timedelta(minutes=2))
    fired = scheduler.dispatch_due(lambda wake: executor.execute(wake, trigger={"mode": "google-oidc", "email": "scheduler@test"}))
    assert [row.kind for row in fired] == ["courier_status_poll"]

    closed = cases.get(case["case_id"])
    assert closed["status"] == "resolved"
    assert closed["delivery"]["confirmed_by"] == "background-wake"
    assert closed["timeline"][-1]["actor"] == "Background wake agent"
    assert closed["background_executions"][0]["trigger"] == "google-oidc"
    receipt = [row for row in scheduler._store.for_run(case["case_id"]) if row.kind == "receipt_followup"][0]
    assert receipt.status is WakeStatus.CANCELLED
    assert receipt.cancelled_reason == "case resolved by courier confirmation"

    proof = public_view(closed)["autonomy_proof"]
    assert proof["closed_by_background_wake"] is True
    assert proof["cloud_scheduler_triggered_executions"] == 1
    assert proof["background_state_changes"] == 1
    assert proof["unclassified_trace_events"] == 0
    assert proof["operator_continue_clicks"] == 0
    assert proof["proof_integrity"] == "verified"


def test_wake_execution_is_idempotent_and_never_reopens_a_resolved_case():
    clock, scheduler, cases = _runtime()
    case = run_unattended_demo(create_case(), courier_eta_minutes=1)
    register_followups(case, scheduler)
    cases.put(case)
    executor = ColdClockWakeExecutor(cases, clock, scheduler)
    clock.advance(timedelta(minutes=2))
    wake = scheduler.dispatch_due(executor.execute)[0]
    first = cases.get(case["case_id"])
    again = executor.execute(wake)
    assert again["outcome"] == "case_closed"
    assert len(cases.get(case["case_id"])["timeline"]) == len(first["timeline"])


def test_http_unattended_demo_registers_wakes_and_advance_can_defer_to_scheduler():
    case = client.post("/api/demo/unattended").json()
    case_id = case["case_id"]
    assert case["status"] == "delivery_dispatched"
    assert case["autonomy"]["closed_by_background_wake"] is False
    wakes = client.get(f"/api/cases/{case_id}/wakes").json()
    assert {row["kind"] for row in wakes["wakes"]} == {"courier_status_poll", "receipt_followup"}
    assert all(row["status"] == "pending" for row in wakes["wakes"])

    deferred = client.post("/api/hardening/advance", json={"minutes": 2, "dispatch": False}).json()
    assert deferred["left_for_scheduler"] is True and deferred["dispatched"] == []
    assert client.get(f"/api/cases/{case_id}").json()["status"] == "delivery_dispatched"

    scan = client.post("/internal/wakes/scan").json()
    assert scan["identity"] == {"mode": "local-test"}
    poll = [row["wake_id"] for row in wakes["wakes"] if row["kind"] == "courier_status_poll"][0]
    assert poll in scan["dispatched"]

    closed = client.get(f"/api/cases/{case_id}").json()
    assert closed["status"] == "resolved"
    assert closed["autonomy"]["closed_by_background_wake"] is True
    assert closed["autonomy"]["background_wakes_fired"] == 1
    assert closed["autonomy_proof"]["closed_by_background_wake"] is True
    statuses = {row["kind"]: row["status"] for row in client.get(f"/api/cases/{case_id}/wakes").json()["wakes"]}
    assert statuses == {"courier_status_poll": "done", "receipt_followup": "cancelled"}


def test_manual_receipt_still_works_and_courier_wake_then_stands_down():
    case = client.post("/api/cases").json()
    case_id = case["case_id"]
    client.post(f"/api/cases/{case_id}/outage")
    client.post(f"/api/cases/{case_id}/review", json={"disposition": "replace", "reviewer_name": "Avery Chen, PharmD - synthetic", "rationale": "Replacement approved for this synthetic automation test."})
    done = client.post(f"/api/cases/{case_id}/confirm-delivery").json()
    assert done["status"] == "resolved" and done["delivery"]["confirmed_by"] == "household"
    statuses = {row["kind"]: row["status"] for row in client.get(f"/api/cases/{case_id}/wakes").json()["wakes"]}
    assert statuses["review_followup"] == "cancelled", "review reminder stands down once the pharmacist decides"
    client.post("/api/hardening/advance", json={"minutes": 61})
    after = client.get(f"/api/cases/{case_id}").json()
    outcomes = {row["kind"]: row["outcome"] for row in after["background_executions"]}
    assert outcomes == {"courier_status_poll": "no_longer_needed", "receipt_followup": "no_longer_needed"}
    assert after["status"] == "resolved"
    assert len(after["timeline"]) == len(done["timeline"])
