# ColdClock impact evidence scorecard

This is a measurement contract, not a claim of clinical benefit. Never replace a pending value with an estimate. Publish only dated receipts from synthetic table-tops or an authorized, protected pilot.

## Impact hypothesis

During a power outage, a household should not have to reconstruct medication storage evidence, locate a qualified decision-maker, arrange an accessible replacement, and prove receipt through disconnected calls. ColdClock should compress that coordination while leaving medication disposition exclusively with a named pharmacist.

## Current executable evidence

| Measure | Required evidence | Acceptance threshold | Current status |
|---|---|---:|---|
| Safe automatic progression | Persisted autonomy receipt | Zero unclassified actors and zero operator-continue events | Automated test implemented |
| Clinical authority protection | Completed and failure-path traces | Zero system medication dispositions | Automated test implemented |
| Lost-update prevention | Two-reader concurrent-write test | Stale writer rejected; newer state preserved | Automated test implemented |
| Recovery from missing sensor/reviewer/stock/courier | Hardening proof endpoint | Every safe-stop check passes | Implemented |
| Durable continuation | Scheduler and wake receipts | One idempotent wake; no duplicate action | Implemented |

## External tabletop protocol

Recruit at least five participants across two roles: pharmacist/pharmacy technician and emergency-preparedness or medication-access staff. Use only the synthetic fixture.

Capture:

1. Median time from excursion event to reviewer-ready packet.
2. Median time from named disposition to reserved accessible delivery.
3. Wrong turns and requests for developer help.
4. Whether the participant believed AI made the clinical decision.
5. Missing evidence or integration blockers.

Targets: at least 80% unassisted completion, median packet readiness under three minutes, zero authority confusion, and no severe safety finding. A severe safety finding blocks any outcome claim until corrected and re-tested.

## Pilot progression

- Stage A: five synthetic tabletop sessions.
- Stage B: shadow-mode exercise with an authorized organization and de-identified data.
- Stage C: protected pilot measuring coordination time against the organization's existing workflow.

No medication quality, adherence, hospitalization, or health-outcome claim is permitted without an appropriately designed study.

## Evidence bundle

For every session store a dated consent-safe receipt containing role, fixture version, start/end timestamps, completion state, autonomy proof, hardening proof version, wrong turns, required change, and an optional approved quotation. Do not store participant names or real medication information in the public repository.
