from pathlib import Path


WEB = Path(__file__).resolve().parent.parent / "web"


def test_landing_page_has_required_trust_sections_and_citations():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert "What ColdClock does not do" in html
    assert "Synthetic public demonstration" in html
    assert "fda.gov" in html and "cdc.gov" in html and "pubmed.ncbi.nlm.nih.gov" in html
    assert "theme-toggle" in html


def test_judge_page_maps_rubric_and_prior_art():
    html = (WEB / "judges.html").read_text(encoding="utf-8")
    assert "Rubric map" in html
    assert "Prior art and contribution" in html
    assert "Executable safety case" in html
    assert "replay evidence" in html


def test_responsive_and_reduced_motion_styles_exist():
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css
    assert "@media (max-width: 760px)" in css
    assert "min-width: 320px" in css
    assert ':root[data-theme="dark"]' in css

