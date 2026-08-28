"""The courier poll is answered by the sandbox courier connector, never by the clock."""
from datetime import timedelta

from fastapi.testclient import TestClient

from cold_clock.followups import register_followups
from cold_clock.store import MemoryCaseStore
from cold_clock.wake_actions import ColdClockWakeExecutor, poll_sandbox_courier
from cold_clock.workflow import create_case, public_view, run_unattended_demo
from service.main import app
from spine.clock import MemoryClockStateStore, SimulatedClock
from spine.wake import MemoryWakeStore, WakeScheduler

client = TestClient(app)


def _runtime():
    clock = SimulatedClock(MemoryClockStateStore())
    scheduler = WakeScheduler(MemoryWakeStore(), clock)
    return clock, scheduler, MemoryCaseStore()


def test_dispatch_creates_a_courier_job_and_polls_are_recorded():
    case = run_unattended_demo(create_case(), courier_eta_minutes=1)
    job = case["delivery"]["courier_job"]
    assert job == {"status": "in_transit", "polls": 0, "delay_polls": 0, "history": []}
    first = poll_sandbox_courier(case, SimulatedClock(MemoryClockStateStore()).now())
    assert first["status"] == "delivered" and case["delivery"]["courier_job"]["polls"] == 1
    assert case["delivery"]["courier_job"]["history"][0]["reported"] == "delivered"


def test_delayed_courier_defers_closure_then_confirms():
    clock, scheduler, cases = _runtime()
    case = create_case(); case["courier_delay_polls"] = 1
    run_unattended_demo(case, courier_eta_minutes=1); register_followups(case, scheduler); cases.put(case)
    executor = ColdClockWakeExecutor(cases, clock, scheduler)
    clock.advance(timedelta(minutes=2)); scheduler.dispatch_due(executor.execute)
    mid = cases.get(case["case_id"])
    assert mid["status"] == "delivery_dispatched" and "received_at" not in mid["delivery"]
    assert mid["background_executions"][-1]["outcome"] == "in_transit_repoll"
    assert mid["timeline"][-1]["action"] == "Courier still in transit"
    assert [row.kind for row in scheduler.pending_for(case["case_id"])] == ["courier_status_poll", "receipt_followup"]
    clock.advance(timedelta(minutes=2)); scheduler.dispatch_due(executor.execute)
    done = cases.get(case["case_id"])
    assert done["status"] == "resolved" and done["delivery"]["confirmed_by"] == "background-wake"
    assert done["delivery"]["courier_job"]["polls"] == 2
    proof = public_view(done)["autonomy_proof"]
    assert proof["background_wake_executions"] == 2 and proof["proof_integrity"] == "verified"


def test_courier_that_never_confirms_becomes_a_bounded_human_hold():
    clock, scheduler, cases = _runtime()
    case = create_case(); case["courier_delay_polls"] = 9
    run_unattended_demo(case, courier_eta_minutes=1); register_followups(case, scheduler); cases.put(case)
    executor = ColdClockWakeExecutor(cases, clock, scheduler)
    for _ in range(8):
        clock.advance(timedelta(minutes=2)); scheduler.dispatch_due(executor.execute)
    held = cases.get(case["case_id"])
    assert held["status"] == "delivery_dispatched"
    assert held["delivery"]["hold"]["system_receipt"] is None
    outcomes = [row["outcome"] for row in held["background_executions"] if row["kind"] == "courier_status_poll"]
    assert outcomes == ["in_transit_repoll", "in_transit_repoll", "in_transit_repoll", "delivery_unconfirmed_hold"]
    pending = [row.kind for row in scheduler.pending_for(case["case_id"])]
    assert "courier_status_poll" not in pending, "no unbounded polling"
    assert pending == ["receipt_followup"], "the human-facing reminder still stands"
    assert public_view(held)["autonomy_proof"]["unclassified_trace_events"] == 0


def test_failure_lab_can_inject_courier_delay_over_http():
    case = client.post("/api/demo/unattended").json()
    delayed = client.post(f"/api/hardening/cases/{case['case_id']}/courier-delay", json={"minutes": 1}).json()
    assert delayed["delivery"]["courier_job"]["delay_polls"] == 1
    client.post("/api/hardening/advance", json={"minutes": 2})
    mid = client.get(f"/api/cases/{case['case_id']}").json()
    assert mid["status"] == "delivery_dispatched" and mid["background_executions"][-1]["outcome"] == "in_transit_repoll"
    client.post("/api/hardening/advance", json={"minutes": 2})
    assert client.get(f"/api/cases/{case['case_id']}").json()["status"] == "resolved"


def test_case_listing_is_newest_first_and_bounded_and_area_query_filters():
    store = MemoryCaseStore()
    for index in range(5):
        case = create_case(); case["opened_at"] = f"2026-08-25T10:0{index}:00Z"; case["service_area"] = "grid-7" if index % 2 else "grid-9"
        store.put(case)
    listed = store.list_cases(limit=3)
    assert [row["opened_at"] for row in listed] == ["2026-08-25T10:04:00Z", "2026-08-25T10:03:00Z", "2026-08-25T10:02:00Z"]
    assert {row["service_area"] for row in store.list_cases_in_area("grid-7")} == {"grid-7"}
    assert len(store.list_cases_in_area("grid-7")) == 2


def test_case_creation_is_throttled_per_network_with_headers():
    response = client.post("/api/cases")
    assert response.status_code == 200 and response.headers["X-Demo-Limit"] == "120"


def test_zero_eta_is_honoured_and_not_replaced_by_the_default():
    """0 minutes means the next scheduler tick; a falsy check would silently make it 34."""
    case = run_unattended_demo(create_case(), courier_eta_minutes=0)
    assert case["delivery"]["eta_minutes"] == 0
