import pytest

from cold_clock.workflow import (
    confirm_delivery,
    create_case,
    dispatch_delivery,
    prepare_fulfillment,
    record_review,
    request_review,
    run_full_demo,
    trigger_outage,
)


def test_case_starts_in_monitoring_with_verified_quotes():
    case = create_case()
    assert case["status"] == "monitoring"
    transcript = case["extraction"]["transcription"]
    assert all(field["quote"] in transcript for field in case["extraction"]["fields"])
    assert case["safety"]["clinical_decision_by_ai"] is False


def test_excursion_records_observations_without_deciding():
    case = create_case()
    trigger_outage(case)
    assert case["status"] == "excursion_detected"
    assert case["excursion"]["maximum_fahrenheit"] == 95.2
    assert case["excursion"]["ai_disposition"] is None


def test_fulfillment_is_impossible_before_human_review():
    case = create_case()
    with pytest.raises(ValueError, match="approved human"):
        prepare_fulfillment(case)


def test_review_requires_excursion():
    with pytest.raises(ValueError, match="recorded excursion"):
        request_review(create_case())


@pytest.mark.parametrize("disposition", ["safe", "discard", "prescribe", "auto_replace", ""])
def test_unsupported_dispositions_are_rejected(disposition):
    case = create_case()
    trigger_outage(case)
    request_review(case)
    with pytest.raises(ValueError, match="unsupported"):
        record_review(case, disposition, "Reviewer Name", "A sufficiently long rationale.")


def test_nonreplacement_decision_does_not_unlock_fulfillment():
    case = create_case()
    trigger_outage(case)
    request_review(case)
    record_review(case, "manufacturer_review", "Reviewer Name", "Escalate to the manufacturer for guidance.")
    assert case["status"] == "review_resolved"
    with pytest.raises(ValueError):
        prepare_fulfillment(case)


def test_full_approved_path_has_receipt_and_ordered_timeline():
    case = run_full_demo()
    assert case["status"] == "resolved"
    assert case["delivery"]["status"] == "received"
    assert case["review"]["decision"]["made_by_ai"] is False
    assert case["fulfillment"]["sandbox"] is True
    assert case["delivery"]["sandbox"] is True
    assert [row["sequence"] for row in case["timeline"]] == list(range(1, 9))


def test_state_machine_blocks_out_of_order_delivery():
    case = create_case()
    with pytest.raises(ValueError, match="prepared replacement"):
        dispatch_delivery(case)
    with pytest.raises(ValueError, match="dispatched delivery"):
        confirm_delivery(case)

