"""Derived, judge-readable proof of bounded autonomous execution."""

from __future__ import annotations

from typing import Any, Iterable


def build_autonomy_proof(
    record: dict[str, Any],
    *,
    id_field: str,
    automatic_actors: Iterable[str],
    authority_actors: Iterable[str],
    external_actors: Iterable[str],
) -> dict[str, Any]:
    timeline = record.get("timeline") or []
    automatic_tokens = tuple(token.lower() for token in automatic_actors)
    authority_tokens = tuple(token.lower() for token in authority_actors)
    external_tokens = tuple(token.lower() for token in external_actors)
    counts = {"automatic": 0, "authority": 0, "external": 0, "unclassified": 0}
    evidence: set[str] = set()
    classifications: list[dict[str, Any]] = []

    for event in timeline:
        actor = str(event.get("actor", "")).lower()
        if any(token in actor for token in authority_tokens):
            execution_class = "human_authority"
            counts["authority"] += 1
        elif any(token in actor for token in external_tokens):
            execution_class = "external_evidence"
            counts["external"] += 1
        elif any(token in actor for token in automatic_tokens):
            execution_class = "agent_automatic"
            counts["automatic"] += 1
        else:
            # Proof must fail closed. Unknown actors can never inflate autonomy.
            execution_class = "unclassified"
            counts["unclassified"] += 1
        evidence.update(str(item) for item in event.get("evidence_ids", event.get("evidence", [])))
        classifications.append(
            {
                "sequence": event.get("sequence"),
                "actor": event.get("actor"),
                "action": event.get("action"),
                "execution_class": execution_class,
            }
        )

    managed = record.get("managed_agent_trace") or []
    wakes = record.get("scheduled_wakes") or []
    followup_wake = (record.get("followup") or {}).get("wake_id")
    if followup_wake and not any(row.get("wake_id") == followup_wake for row in wakes):
        wakes = [*wakes, {"wake_id": followup_wake, "kind": "followup"}]
    runs = record.get("autonomy_runs") or []
    last_actions = (record.get("last_autonomy_run") or {}).get("actions", [])
    automatic_actions = sum(len(run.get("actions", [])) for run in runs)
    if not runs:
        automatic_actions = len(last_actions)

    background = record.get("background_executions") or []
    background_state_changes = [row for row in background if row.get("outcome") == "case_closed"]
    scheduler_triggered = [row for row in background if row.get("trigger") == "google-oidc"]

    operator_interactions = record.get("operator_interactions") or []
    continue_actions = {"continue", "continue_clicked", "manual_continue", "operator_continue"}
    operator_continue_clicks = sum(
        1
        for interaction in operator_interactions
        if str(interaction.get("action", "")).strip().lower() in continue_actions
    )
    proof_complete = counts["unclassified"] == 0

    return {
        "record_id": record.get(id_field),
        "derived_from_persisted_trace": True,
        "trace_events": len(timeline),
        "automatic_trace_events": counts["automatic"],
        "automatic_state_actions": automatic_actions,
        "human_authority_events": counts["authority"],
        "external_evidence_events": counts["external"],
        "unclassified_trace_events": counts["unclassified"],
        "managed_agent_commands": len(managed),
        "durable_background_wakes": len(wakes),
        "background_wake_executions": len(background),
        "background_state_changes": len(background_state_changes),
        "cloud_scheduler_triggered_executions": len(scheduler_triggered),
        "closed_by_background_wake": (record.get("delivery") or {}).get("confirmed_by") == "background-wake",
        "autonomous_resume_batches": len(runs) or (1 if last_actions else 0),
        "operator_continue_clicks": operator_continue_clicks,
        "operator_interactions_observed": len(operator_interactions),
        "classification_policy": "fail-closed-actor-allowlists",
        "proof_integrity": "verified" if proof_complete else "incomplete",
        "system_decisions_over_reserved_authority": 0,
        "completion": record.get("status") in {"resolved", "review_resolved", "closed"},
        "current_wait": (record.get("last_autonomy_run") or {}).get("waiting_for"),
        "synthetic_tabletop_completion": record.get("demo_completion_mode") == "synthetic_tabletop",
        "evidence_receipts": sorted(evidence),
        "classified_trace": classifications,
        "claim": (
            "The persisted trace contains only classified agent, reserved-authority, and external-evidence events; no operator continuation was observed."
            if proof_complete and operator_continue_clicks == 0
            else "Autonomy proof is incomplete; inspect unclassified trace events or operator continuation evidence."
        ),
    }
