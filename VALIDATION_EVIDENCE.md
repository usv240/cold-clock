# ColdClock: Validation Evidence

## Verified locally on August 16, 2026

| Gate | Result | Command or endpoint |
|---|---:|---|
| Python tests | 111 passed | `python -m pytest -q` |
| Static accessibility checks | 10/10 | `python scripts/check_a11y.py` |
| Executable HTTP demonstration | 12/12 | `python scripts/demo_flow.py --url http://127.0.0.1:8041` |
| Foundational safety proof | 8/8 |
| Adversarial hardening proof | 8/8 | `GET /api/proof` |
| Pre-approval fulfillment | Blocked with conflict | test and demo flow |
| Unsupported disposition | Rejected | unit and public proof |
| AI clinical disposition | Absent | state, test, health and judge pages |
| End-to-end approved flow | Receipt confirmed | test and demo flow |

## Deployed verification

- Public service: https://cold-clock-109051079423.us-central1.run.app
- Revision verified after deployment: `cold-clock-00013-dqj`.
- `/health`: `firestore`, `gemini-3.5-flash`, `human-only`, transactional wakes, active Cloud Trace.
- Public acceptance: `12/12`; foundational proof: `8/8`; hardening proof: `8/8`; landing, verification console, and architecture brief: HTTP 200.
- Startup smoke proof: two user-created cases persisted in the queue; a 45-minute event was calculated from supplied timestamps; an identical delivery was acknowledged as a duplicate without adding timeline entries; named human review reached `replacement_approved` with `made_by_ai=false`.
- Public safety boundary: synthetic-only readiness mode; de-identified intake and global reset both returned HTTP 403.

## Not yet validated

- The live Gemini recording passed `4/4` adjacent truth checks; broader package coverage is untested.
- No pharmacist has reviewed the interface or disposition taxonomy.
- No live structured-label API failure test has been run.
- No real pharmacy, insurer, sensor, utility, or courier integration exists.
- Rendered browser QA is pending because the current browser connection was blocked by an
  environment ACL helper during this build session.
- No patient outcome or workflow-time improvement has been measured.

## Required external validation

1. Pharmacist reviews the case packet, safe stops, terminology, and five dispositions.
2. At least three medication fixtures are recorded live and graded against adjacent truth.
3. Tabletop cases cover heat, freezing, missing readings, repeated excursions, unknown package,
   unavailable reviewer, unavailable stock, and failed delivery.
4. Public Cloud Run acceptance flow passes from a clean unauthenticated browser.
5. Keyboard, screen-reader, 320/375/768/1024/1440 layouts, and both themes are visually reviewed.

## Hardened runtime evidence

- Missing sensor history stops with no inferred temperature or disposition.
- Reviewer, matching-stock, and courier failures preserve the relevant human gate.
- Wake registration is deterministic; transactional claims, leases, retry limits, cancellation audit, and dead letters are tested.
- The deployed service returns an active Cloud Trace status and a per-request trace header.
- Firestore composite indexes for due and expired-lease scans are checked into `app/infra` and provisioned.

