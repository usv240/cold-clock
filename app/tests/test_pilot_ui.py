from pathlib import Path


WEB = Path(__file__).resolve().parent.parent / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
JS = (WEB / "app.js").read_text(encoding="utf-8")
CSS = (WEB / "styles.css").read_text(encoding="utf-8")


def test_landing_exposes_multi_case_pilot_workspace():
    assert "Pilot operations workspace" in HTML
    assert 'id="case-select"' in HTML
    assert 'id="new-case"' in HTML
    assert 'id="record-sensor"' in HTML
    assert "/api/pilot/readiness" in HTML


def test_intake_event_and_human_review_are_real_inputs():
    assert 'id="intake-form"' in HTML
    assert 'name="package_transcription"' in HTML
    assert 'id="sensor-form"' in HTML
    assert 'name="event_id"' in HTML
    assert 'id="review-form"' in HTML
    assert 'name="reviewer_name"' in HTML
    assert 'name="rationale"' in HTML


def test_ui_preserves_cases_and_uses_pilot_endpoints():
    assert 'api("/api/reset"' not in JS
    assert 'api("/api/pilot/cases"' in JS
    assert "/sensor-events" in JS
    assert "refreshCases" in JS
    assert "showModal" in JS


def test_pilot_ui_is_responsive_and_theme_native():
    assert ".pilot-toolbar" in CSS
    assert ".pilot-dialog" in CSS
    assert ".form-grid" in CSS
    assert "@media (max-width: 760px)" in CSS
