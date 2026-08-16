from cold_clock.failures import (
    choose_accessible_courier,
    mark_reviewer_unavailable,
    report_courier_unavailable,
    report_sensor_gap,
    report_stock_unavailable,
    resolve_matching_stock,
    resume_human_review,
)
from cold_clock.workflow import (
    create_case,
    prepare_fulfillment,
    record_review,
    request_review,
    trigger_outage,
)


def reviewed_case():
    case = create_case()
    trigger_outage(case)
    request_review(case)
    record_review(case, "replace", "Avery Chen - synthetic", "Human fixture decision.")
    return case


def test_sensor_gap_is_a_safe_stop_without_invented_values():
    case = create_case()
    report_sensor_gap(case)
    assert case["status"] == "evidence_incomplete"
    assert case["sensor"]["readings"][-1]["fahrenheit"] is None
    assert case["safe_stop"]["system_disposition"] is None
    assert case["timeline"][-1]["status"] == "blocked"


def test_sensor_gap_rejects_wrong_state():
    case = create_case()
    trigger_outage(case)
    try:
        report_sensor_gap(case)
    except ValueError as exc:
        assert "monitoring" in str(exc)
    else:
        raise AssertionError("unsafe transition accepted")


def test_unavailable_reviewer_preserves_human_gate_and_can_resume():
    case = create_case()
    trigger_outage(case)
    request_review(case)
    mark_reviewer_unavailable(case)
    assert case["review"]["decision"] is None
    assert case["review"]["escalation"]["external_message_sent"] is False
    resume_human_review(case)
    assert case["review"]["status"] == "pending_human"


def test_stock_failure_never_substitutes():
    case = reviewed_case()
    report_stock_unavailable(case)
    assert case["fulfillment"]["system_substitution"] is None
    assert case["status"] == "stock_escalated"
    resolve_matching_stock(case)
    assert case["fulfillment"]["alternate_match_verified"] is True


def test_stock_failure_requires_human_replacement_decision():
    case = create_case()
    try:
        report_stock_unavailable(case)
    except ValueError as exc:
        assert "human-approved" in str(exc)
    else:
        raise AssertionError("stock search bypassed human gate")


def test_courier_failure_leaves_choice_to_named_human():
    case = reviewed_case()
    prepare_fulfillment(case)
    report_courier_unavailable(case)
    assert case["delivery"]["system_selected_alternative"] is None
    choose_accessible_courier(case, "Morgan - synthetic")
    assert case["delivery"]["selected_by_ai"] is False
    assert case["delivery"]["selected_by"] == "Morgan - synthetic"


def test_courier_choice_requires_name():
    case = reviewed_case()
    prepare_fulfillment(case)
    report_courier_unavailable(case)
    try:
        choose_accessible_courier(case, "x")
    except ValueError as exc:
        assert "named human" in str(exc)
    else:
        raise AssertionError("anonymous choice accepted")

