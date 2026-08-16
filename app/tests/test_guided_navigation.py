from pathlib import Path


WEB = Path(__file__).parents[1] / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "app.js").read_text(encoding="utf-8")
GUIDE = (WEB / "guide.js").read_text(encoding="utf-8")
STYLE = (WEB / "guide.css").read_text(encoding="utf-8")


def test_guided_entry_and_assets_are_visible():
    assert 'id="start-guide"' in HTML
    assert 'href="/static/guide.css"' in HTML
    assert 'src="/static/guide.js"' in HTML
    assert "Guide me step by step" in HTML


def test_guide_observes_the_real_workflow_state():
    assert "workflowState" in APP
    assert "data-workflow-state" in GUIDE
    assert "MutationObserver" in GUIDE


def test_guide_has_navigation_and_accessibility_controls():
    for control in ("show", "back", "restart", "exit", "expand"):
        assert f'data-guide-action="{control}"' in GUIDE
    assert 'aria-live="polite"' in GUIDE
    assert "Escape" in GUIDE
    assert "prefers-reduced-motion" in STYLE


def test_guide_points_without_automating_consequential_clicks():
    assert "scrollIntoView" in GUIDE
    assert "guided-target" in GUIDE
    assert "target.click()" not in GUIDE
    assert "inline_model_armor" not in GUIDE
