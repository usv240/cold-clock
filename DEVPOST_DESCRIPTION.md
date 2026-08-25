# Devpost submission text — ColdClock (paste-ready)

**Category:** The Taskmaster
**Hosted project:** https://cold-clock-109051079423.us-central1.run.app
**Repository:** https://github.com/usv240/cold-clock
**Video:** _(public YouTube/Vimeo URL, under four minutes)_

## Inspiration

When a refrigerator or the power fails, a home with insulin or another temperature-sensitive medicine gets an alarm — and then nothing. Someone still has to identify the exact product and lot, reconstruct how long it was out of range, find the current storage guidance, reach a pharmacist, arrange an approved replacement, and prove it arrived. Monitoring products stop at the alert. ColdClock starts there.

## What it does

ColdClock is an event-driven agent that carries a medication excursion from the first out-of-range reading to a closed case:

1. **Observes precisely.** Gemini 3.5 Flash reads the synthetic package with exact-quote grounding (every retained field must appear verbatim in the model's own transcription). Package text is treated as untrusted: a deterministic pattern layer plus Gemma 4 quarantine any instruction-shaped spans before the text goes anywhere. Gemini Embedding 001 routes the evidence toward label evidence, professional review, or fulfillment.
2. **Routes for judgment.** One sensor excursion — or one utility-outage message on Pub/Sub, fanned out to every enrolled household in the grid area — triggers a background watch that judges each case from its own readings. A Google ADK agent then assembles the review packet through three scoped read-only tools; a verifier checks every value against tool output and rejects any invented number or safety claim before the packet reaches a named pharmacist. The agent never chooses a disposition; the state machine makes fulfillment impossible until a human does.
3. **Finishes without supervision.** One human decision automatically reserves matching sandbox inventory and books an accessible courier slot. Then a durable `courier_status_poll` wake is registered in Firestore. Cloud Scheduler calls the OIDC-protected worker every minute; at the ETA the worker polls the sandbox courier, records the handoff, resolves the case, and cancels the now-pointless reminder. Nobody clicks. The UI updates by itself.
4. **Proves it.** Every case carries a public action trace and an autonomy receipt derived from the persisted timeline: `operator_continue_clicks: 0`, `closed_by_background_wake: true`, `cloud_scheduler_triggered_executions: 1`, `proof_integrity: verified`. Unknown actors fail the proof closed instead of inflating it, and the receipt is HMAC-signed so a copy can be verified against the service.

## How we built it

- **Cloud Run** hosts one FastAPI service; roles (intake, monitor, live evidence, guardrail, excursion, review packet, fulfillment, logistics, background wake) are modules with a typed, bounded state contract (out-of-order actions return HTTP 409).
- **Firestore** holds cases with optimistic record versions (a stale concurrent write is rejected, not merged) and wake rows claimed in transactions with a 90-second lease, five bounded attempts, and a dead-letter path.
- **Cloud Scheduler** drives the background worker every minute with a Google-signed OIDC token; the app verifies audience, issuer, and the dedicated service-account email and returns 401 otherwise. **Pub/Sub** push subscriptions deliver sensor and utility events to the same verifier.
- **Google ADK** runs the review-packet agent: an `LlmAgent` with three scoped read-only tools and a post-model verifier, so the model's reasoning is used only where it can be checked.
- **Vertex AI via the Google Gen AI SDK** for all three models: Gemini 3.5 Flash (extraction and the ADK agent), Gemini Embedding 001 (routing), Gemma 4 (injection screen). Extraction and routing fail closed — recorded fixtures are test-only and are never substituted in the deployment.
- **Secret Manager** injects the HMAC pepper for developer API keys and network fingerprints; **Cloud Trace** correlates every request.
- A persisted, forward-only **simulated clock** lets a four-minute demo reach a 34-minute courier ETA using the exact code path production uses; the UI states that the clock is simulated.

## Challenges

- Finishing a workflow in one HTTP request is not autonomy. Moving the receipt from a click to a scheduler-fired courier poll — and then proving it from persisted state rather than from anything the caller asserts — was the real work.
- A wake-fired timeline entry with an unlisted actor silently broke the fail-closed autonomy proof; naming the worker as an agent and testing the proof after a wake fires caught it.
- Cloud Run answers at two URLs; the scheduler's OIDC audience must match the one the app expects. A deploy that reset the audience produced silent 401s until the worker accepted every configured form.
- Keeping a small model useful and harmless: Gemma may only return verbatim spans that exist in the text, so its output is checkable and it has no route to a decision.

## Accomplishments

- 158 automated tests; 21/21 executable acceptance checks against the live deployment, including a case closed by a genuine Cloud Scheduler tick and a grid outage fanned out across enrolled cases; 8/8 safety proof and 17/17 hardening proof (sensor gap, reviewer failure, stock miss, courier failure, idempotent wakes, unattended closure, quarantine, packet-verifier rejection, outage fan-out and safe stop).
- Live, graded model evidence: Gemini 5/5 fields with 0 invented; Gemma 3/3 on clean and poisoned labels.
- A keyless judge UI plus a self-service `/v1` developer API with per-key and per-network quotas.

## What we learned

The most valuable behaviour is continuity — evidence, authority, inventory, accessibility, receipt — not a temperature prediction. Exact-quote extraction only earns trust when rejected fields stay visible and incomplete history becomes a safe stop. Durable action needs deterministic registration, transactional claiming, and idempotent action records.

## What's next

Real sensor-gateway and utility partners on the existing Pub/Sub topics, a private identity-controlled deployment for authorized de-identified pilots, pharmacist review of the packet and disposition taxonomy, and more medication fixtures recorded and graded live.

## Technologies

Gemini 3.5 Flash · Gemini Embedding 001 · Gemma 4 (Vertex AI MaaS) · Google ADK · Google Gen AI SDK · Cloud Run · Firestore · Cloud Scheduler · Pub/Sub · Cloud Trace · Secret Manager · FastAPI · Python 3.12

## Data sources

Synthetic package, sensor, people and sandbox connectors only. Public guidance is cited for the problem, never as validation: FDA disaster drug-use guidance, CDC emergency insulin guidance, a Cochrane review on insulin thermal stability, a Hurricane Maria community study, the QChainMED monitoring pilot, NHS SPS excursion workflow, and the DailyMed structured label for the fixture product.

## Disclosure

Generic clock, wake, observability, quarantine and verifier primitives were adapted from the entrant's own contest-period shared spine (disclosed in `app/spine/__init__.py`). Everything else was built for this submission during the submission period. ColdClock is an independent prototype; no cited organisation endorses it, and no clinical outcome is claimed.
