from datetime import datetime, timezone

from cold_clock.pilot import create_pilot_case
from cold_clock.workflow import request_review, trigger_outage


def test_pilot_audit_timestamps_use_realtime_case_clock():
    intake = {
        "data_use_acknowledgement": True,
        "data_class": "synthetic",
        "case_reference": "Realtime pilot",
        "contact_preference": "portal",
        "mobility_note": "",
        "medication": {"display_name": "Example medicine", "strength": "10 mg/mL", "form": "vial", "lot": "RT-1", "opened_on": "Not provided"},
        "package_transcription": "Example medicine\n10 mg/mL\nvial\nRT-1",
        "label_source_title": "Authorized label",
        "label_source_url": "https://example.test/label",
        "jurisdiction": "United States",
        "quoted_storage_text": "Store from 36 to 46 degrees Fahrenheit.",
        "monitoring_range_f": {"minimum": 36, "maximum": 46},
        "baseline_fahrenheit": 41,
        "sensor_source": "Test sensor",
    }
    before = datetime.now(timezone.utc)
    case = create_pilot_case(intake)
    trigger_outage(case)
    request_review(case)
    after = datetime.now(timezone.utc)
    for row in case["timeline"]:
        moment = datetime.fromisoformat(row["at"].replace("Z", "+00:00"))
        assert before <= moment <= after
    requested = datetime.fromisoformat(case["review"]["requested_at"].replace("Z", "+00:00"))
    assert before <= requested <= after
