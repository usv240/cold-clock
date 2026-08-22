"""Build a public, privacy-safe execution trace from the durable workflow timeline."""
from __future__ import annotations

from typing import Any


def public_action_trace(record: dict[str, Any], record_id_key: str) -> dict[str, Any]:
    events = []
    for row in record.get("timeline", []):
        evidence = [str(item) for item in row.get("evidence_ids", [])]
        events.append(
            {
                "sequence": int(row["sequence"]),
                "at": row["at"],
                "actor": row["actor"],
                "action": row["action"],
                "status": row.get("status", "complete"),
                "evidence_ids": evidence,
                "evidence_count": len(evidence),
            }
        )
    return {
        "record_id": record[record_id_key],
        "visibility": "public-synthetic-action-trace",
        "events": events,
        "event_count": len(events),
        "redaction_policy": {
            "included": ["actor", "action", "state", "timestamp", "evidence identifiers"],
            "excluded": ["raw prompts", "hidden reasoning", "credentials", "personal data", "stack traces"],
        },
        "note": "This is a structured action receipt, not unrestricted application or model logs.",
    }
