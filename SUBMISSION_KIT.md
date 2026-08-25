# ColdClock: Submission Kit

## Devpost one-liner

ColdClock turns a refrigerator or power failure into a pharmacist-reviewed medication resolution
workflow—evidence, approval, replacement, delivery, and a scheduler-fired courier confirmation—without
letting AI make the clinical decision and without anyone having to click "continue".

## Problem

Temperature monitoring ends with an alert, while the patient still has to identify the exact
medicine, reconstruct the excursion, find current evidence, reach a professional, arrange an
approved replacement, and solve delivery. ColdClock closes that operational gap.

## Innovation

The contribution is not a universal medicine-safety model. It is the stateful post-alert resolution
loop with quote-grounded evidence, a code-enforced professional gate, durable background execution
that finishes the case on its own, and proof of completed action.

## Four-minute video (live, unedited; total under 3:50)

| Time | Beat | On screen |
|---|---|---|
| 0:00–0:20 | The alert-versus-resolution problem and the human-authority boundary | Landing page, `.run.app` address bar visible |
| 0:20–0:45 | Click **Run unattended**. Live Gemini reads the synthetic package (5 exact-quoted fields); Gemma screens the text; Embedding routes it | Medicine evidence tab: verified fields, injection screen "clean", timeline entries |
| 0:45–1:10 | The outage is recorded; the packet routes itself; the synthetic pharmacist decision is recorded; reservation and dispatch happen automatically | Journey rail advancing, `AI disposition: none` |
| 1:10–1:25 | Stop. Point at the **Durable wakes** panel: `courier_status_poll · pending · due …`. Say: "Nobody clicks from here." | Wake panel, autonomy rail `0 continue clicks` |
| 1:25–2:25 | Switch to Google Cloud Console: Cloud Run service and revision, Cloud Scheduler job `cold-clock-wake-scan` (every minute, OIDC), Firestore `cold_clock_wakes` document, a Cloud Run log line for `/internal/wakes/scan` | Console tabs, then Firestore document flipping `pending → done` |
| 2:25–2:45 | Switch back: the case is **resolved**, timeline shows "Background wake agent · Courier confirmed handoff", autonomy rail says "Closed by a Cloud Scheduler wake — no operator", background wakes `1 fired · closed case` | Product UI (it updated by itself) |
| 2:45–3:10 | Deliberate failure: poisoned package text quarantined; pre-approval fulfillment rejected with 409; sensor gap safe stop | `/api/hardening/proof` 12/12 |
| 3:10–3:35 | Open `/api/cases/{id}/autonomy-proof`: `closed_by_background_wake: true`, `cloud_scheduler_triggered_executions: 1`, `operator_continue_clicks: 0`, `proof_integrity: verified`; open the Cloud Trace entry | JSON and Trace |
| 3:35–3:50 | Limitations and the promise: synthetic connectors, pharmacist authority, no outcome claim; repo and diagram | README architecture |

Pre-flight: run `python scripts/demo_flow.py --url <run.app> --wait-for-scheduler 180` once before recording so the live scheduler path is proven green that day; keep the Console tabs open in advance.

## Required submission proof

- public `.run.app` URL;
- approximately four-minute public video;
- visible Cloud Run revision, Cloud Scheduler job, and Firestore wake document;
- live `/api/demo/unattended` Gemini 3.5 + Embedding 001 + Gemma 4 receipts and adjacent graded recordings;
- architecture diagram;
- public repository and reproducible commands;
- explicit synthetic connector and no-clinical-advice statements;
- public build article with required contest language.
