"""Make and grade one explicit live Gemini 3.5 Flash package recording."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cold_clock.reader import PackageReader, VertexPackageClient

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT is required")
    path = Path(args.image)
    mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    result = PackageReader(VertexPackageClient(project)).read(path.read_bytes(), mime)
    truth = json.loads((ROOT / "fixtures" / "package.truth.json").read_text(encoding="utf-8"))
    expected = {key: str(value).casefold() for key, value in truth.items() if key != "synthetic"}
    actual = {row["key"]: row["value"].casefold() for row in result.fields}
    checks = {key: actual.get(key) == value for key, value in expected.items()}
    recording = {
        "model": "gemini-3.5-flash",
        "mode": "recorded-live-vertex-ai",
        "synthetic": True,
        "transcription": result.transcription,
        "fields": result.fields,
        "dropped": result.dropped,
    }
    report = {"matched": sum(checks.values()), "total": len(checks), "checks": checks}
    (ROOT / "fixtures" / "package.recording.json").write_text(json.dumps(recording, indent=2), encoding="utf-8")
    (ROOT / "fixtures" / "package.accuracy.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())



