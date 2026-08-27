"""Drive the product in a real browser the way a judge would, and fail on any page error.

    python -m pip install playwright && python -m playwright install chromium
    python scripts/browser_check.py --url https://cold-clock-109051079423.us-central1.run.app --wait 240

Steps: Run unattended -> the run stops at the human gate -> the reviewer dialog is submitted ->
hands off -> the page must update by itself to the scheduler-closed state within --wait seconds.
Screenshots go to --out.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--wait", type=int, default=240)
    parser.add_argument("--out", default="browser-check")
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed; see the docstring"); return 2
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    busy_off = "document.querySelector('#console').getAttribute('aria-busy')==='false'"
    checks: list[tuple[str, bool]] = []

    def check(name: str, value: bool) -> None:
        checks.append((name, bool(value))); print(f"{'PASS' if value else 'FAIL'}  {name}")

    with sync_playwright() as p:
        browser = p.chromium.launch(); page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(args.url, wait_until="networkidle")
        page.click("#unattended-demo"); page.wait_for_function(busy_off, timeout=180000)
        check("unattended run stops at the human gate", "pharmacist" in page.text_content("#status-title").lower())
        check("human-gate button is enabled", page.evaluate("!document.querySelector('#next-action').disabled"))
        page.locator("#console").screenshot(path=str(out / "review.png"))  # the board shows the review packet without tabs
        packet = page.text_content("#packet-agent") or ""
        check("packet card shows a receipt", "packet" in packet.lower())
        page.click("#next-action"); page.wait_for_selector("#review-dialog[open]")
        page.fill("#review-form [name=reviewer_name]", "Avery Chen, PharmD - synthetic")
        page.fill("#review-form [name=rationale]", "Replacement approved after reviewing the packet in this browser check.")
        page.click("#review-form button[type=submit]"); page.wait_for_function(busy_off, timeout=60000); time.sleep(1)
        check("one decision dispatched automatically", "delivery" in page.text_content("#status-title").lower())
        page.locator("#console").screenshot(path=str(out / "dispatched.png"))
        started = time.time()
        try:
            page.wait_for_function("document.querySelector('#status-title').textContent.includes('Resolution complete')", timeout=args.wait * 1000)
            closed = True
        except Exception:  # noqa: BLE001
            closed = False
        check(f"page closed itself from a background wake within {args.wait}s", closed)
        if closed:
            print(f"      closed after {time.time() - started:.0f}s: {page.text_content('#autonomy-title')}")
        page.locator("#console").screenshot(path=str(out / "closed.png"))
        check("worker status line reports the scheduler", "scheduler" in (page.text_content("#worker-status") or "").lower())
        check("no page errors", not errors)
        browser.close()
    for error in errors:
        print("PAGEERROR:", error)
    print(f"\n{sum(v for _, v in checks)}/{len(checks)} browser checks passed")
    return 0 if all(v for _, v in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
