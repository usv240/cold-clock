"""Make and grade explicit live Gemini 3.5 Flash package recordings.

    python scripts/record_package.py --image web/package-fixture.png
    python scripts/record_package.py --all      # every fixture with an adjacent truth file

Each recording is graded against its truth file and written next to it. Recordings are test-only;
the deployed workflow always calls Gemini live.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cold_clock.reader import PackageReader, VertexPackageClient

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_TRUTH = {
    "package-fixture.png": ("package.truth.json", "package.recording.json", "package.accuracy.json"),
    "package-fixture-liraglutide.png": ("package-liraglutide.truth.json", "package-liraglutide.recording.json", "package-liraglutide.accuracy.json"),
    "package-fixture-adalimumab.png": ("package-adalimumab.truth.json", "package-adalimumab.recording.json", "package-adalimumab.accuracy.json"),
}


def grade(project: str, image: Path) -> dict:
    truth_name, recording_name, accuracy_name = FIXTURE_TRUTH[image.name]
    mime = "image/svg+xml" if image.suffix.lower() == ".svg" else "image/png"
    result = PackageReader(VertexPackageClient(project)).read(image.read_bytes(), mime)
    truth = json.loads((ROOT / "fixtures" / truth_name).read_text(encoding="utf-8"))
    expected = {key: str(value).casefold() for key, value in truth.items() if key != "synthetic"}
    actual = {row["key"]: row["value"].casefold() for row in result.fields}
    checks = {key: actual.get(key) == value for key, value in expected.items()}
    invented = [row["key"] for row in result.fields if row["quote"] not in result.transcription]
    recording = {"model": "gemini-3.5-flash", "mode": "recorded-live-vertex-ai", "synthetic": True, "image": image.name, "transcription": result.transcription, "fields": result.fields, "dropped": result.dropped}
    report = {"image": image.name, "matched": sum(checks.values()), "total": len(checks), "invented": len(invented), "checks": checks}
    (ROOT / "fixtures" / recording_name).write_text(json.dumps(recording, indent=2), encoding="utf-8")
    (ROOT / "fixtures" / accuracy_name).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT is required")
    images = [ROOT / "web" / name for name in FIXTURE_TRUTH] if args.all else [Path(args.image)]
    reports = [grade(project, image) for image in images]
    for report in reports:
        print(json.dumps(report, indent=2))
    matched = sum(r["matched"] for r in reports); total = sum(r["total"] for r in reports)
    print(f"\n{matched}/{total} fields matched across {len(reports)} fixture(s); invented={sum(r['invented'] for r in reports)}")
    return 0 if matched == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
