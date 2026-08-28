# Rules compliance — ColdClock

| Rules.md requirement | Evidence | Status |
|---|---|---|
| One category | The Taskmaster | Pass |
| Gemini 3.5+ via Gemini API or Vertex AI | Deployed `/api/demo/full` and `/api/demo/unattended` return live fail-closed Gemini 3.5 Flash receipts (`extraction.mode = live-vertex-ai`), plus adjacent truth/accuracy files | Pass |
| Google agent framework | **Google ADK** `LlmAgent` assembles the review packet through three scoped read-only tools with a post-model verifier (`packet_agent` receipt on every case); Google Gen AI SDK for every other model call | Pass |
| Google Cloud service | Cloud Run, Firestore, Cloud Scheduler, Pub/Sub, Cloud Trace, Secret Manager — inventory at `/health` | Pass |
| Runs asynchronously in the background | Cloud Scheduler calls the OIDC-verified worker every minute; the `courier_status_poll` wake closes a dispatched case at the ETA with no operator; `outage_watch` wakes judge every affected case after a grid event; proof at `GET /api/cases/{id}/wakes` and `autonomy_proof.cloud_scheduler_triggered_executions` | Pass |
| Monitors events / handles scale | Pub/Sub push ingress (`/internal/events/sensor`, `/internal/events/utility`); one utility message fans out to every enrolled case in the area | Pass |
| Autonomous workflow beyond chat | Event → evidence → human gate → sandbox fulfillment → dispatch → scheduler-fired courier confirmation → closed case | Pass |
| Working public access | Public product, operations workspace, OpenAPI and proof endpoints; no login | Pass |
| Public repository | https://github.com/usv240/cold-clock | Pass |
| Reproducible setup | README commands, Dockerfile, deploy script, scheduler provisioning script, Firestore indexes | Pass |
| Architecture diagram | `docs/architecture.svg` (Gemini, Embedding, Gemma, Cloud Run, Firestore, Scheduler, Trace, human gate) | Pass |
| Data-source disclosure | README research ledger and per-source claim boundaries | Pass |
| Findings and learnings | README section and validation ledger | Pass |
| New-work disclosure | README identifies the reused production-spine primitives and independent work; first commit 2026-08-16 | Pass |
| Under-four-minute public video | Published by the entrant with live Cloud execution visible: https://youtu.be/iA2KmVMKc-M | Met |
| Additional Google AI models (+0.2 each) | Gemini Embedding 001 (semantic routing) and Gemma 4 (injection screen) both run live in the deployed workflow with receipts; recorded and graded evidence in `app/fixtures` | Implemented; live evidence recorded |
| Optional public content/social post | Drafts are in `docs/`; eligible platform publication remains entrant action | Entrant action |

ColdClock uses only fictional people and synthetic operational connectors. It makes no clinical outcome claim.

## Judging-criteria evidence map

| Criterion | Where a judge can verify it in under a minute |
|---|---|
| Innovation & operational utility (40%) | Click **Run unattended**: the ADK agent assembles the packet, the synthetic pharmacist decision is recorded, reservation and dispatch happen, and within about two minutes the Cloud Scheduler wake closes the case while nothing is clicked. Click **Simulate grid outage**: one event, every enrolled household, each judged by its own background wake. Autonomy rail shows `0 continue clicks`. |
| Architectural discipline (30%) | `TECHNICAL_DESIGN.md`; ADK tools are read-only closures scoped to one case and every model value is verified; optimistic-version Firestore writes (HTTP 409 on stale); transactional wake claims with leases, bounded retry and dead letters; OIDC-verified worker and Pub/Sub ingress; Secret Manager pepper; signed receipts; `/api/hardening/proof` 17/17. |
| Demo & production readiness (30%) | `/health` inventory, `/api/proof`, `/api/hardening/proof`, `/api/cases/{id}/wakes`, signed `/autonomy-proof` + `/api/receipts/verify`, Cloud Run revision, Cloud Scheduler job and Pub/Sub subscriptions visible in console, `demo_flow.py --wait-for-scheduler`, `publish_event.py`. |

## Additional production evidence

| Requirement | Implementation | Status |
|---|---|---|
| Self-service integration | Keyless judge UI plus protected `/v1`, no account required, 50 requests per key and network per UTC day; `/v1/unattended-runs` for integrators | Pass |
| Secure public endpoint | HMAC-only keys, fingerprint-only IP handling, Secret Manager pepper, atomic Firestore quota transactions | Pass |
| Prompt-injection guardrail | Pattern layer plus Gemma 4 quarantine instruction-shaped package text before routing; spans shown, never followed | Pass |
| Visible autonomy | Cumulative trace-derived receipt, background-execution counts, direct proof endpoint, zero continue-click count, honest synthetic-event disclosure | Pass |
