# ColdClock: Validation Evidence

## Verified on August 25, 2026 — agentic release (ADK, Pub/Sub fan-out, signed receipts)

| Gate | Result | Command or endpoint |
|---|---:|---|
| Python tests | 159 passed | `cd app; python -m pytest -q` |
| Static accessibility checks | 10/10 | `python scripts/check_a11y.py` |
| Executable HTTP demonstration, **live with real Cloud Scheduler tick** | 21/21 | `python scripts/demo_flow.py --url https://cold-clock-109051079423.us-central1.run.app --wait-for-scheduler 240` |
| Foundational safety proof | 8/8 | `GET /api/proof` |
| Adversarial hardening proof | 17/17 | `GET /api/hardening/proof` |
| Container dependency resolution | clean | `google-adk==1.3.0` resolved and executed alongside the pinned Firestore/api-core set in a fresh venv |

### Live ADK review-packet agent (final revision `cold-clock-00046-lj2`; first verified on `cold-clock-00040-hck`)

Case `cc-74520e5a757d4a3f9cba4fd44a959e25`, `POST /api/demo/unattended`: `packet_agent` = `{framework: google-adk, model: gemini-3.5-flash, live: true, accepted: true, tool_calls: [get_verified_package_fields, get_excursion_observation, get_label_storage_excerpt], verified_fields: 6, rejected_fields: []}`. The agent's question was used verbatim: "Which reviewed disposition should govern this synthetic case?". Warm latency of the ADK step: 5.3–5.6 s; whole unattended request 14–24 s warm, ~30 s cold. A `ThinkingConfig(thinking_level=...)` tweak was rejected by the container's google-genai build (ValidationError) and silently downgraded packets to the deterministic path until the `packet_agent` receipt exposed it; reverted, re-verified 21/21.

### Live Pub/Sub fan-out

Two fresh monitoring cases (`cc-379671ed…`, `cc-a461e488…`) in the default `grid-7` area. `python scripts/publish_event.py utility --service-area grid-7` published message `21084840278305256` with `outage_id: out-990daf21`. Twelve seconds later both cases carried `utility_outage.channel = pubsub` and one pending `outage_watch` wake each; the Cloud Run log shows `POST /internal/events/utility` → 200 from the push subscription's OIDC identity. A control fan-out through `POST /api/demo/outage-fanout` behaved identically with `channel = api`.

### Signed receipts

`GET /api/cases/{id}/autonomy-proof` returned `signature` `4cb02b1579e29512…`; `POST /api/receipts/verify` returned `valid: true` for the genuine copy and `valid: false` after `operator_continue_clicks` was edited to 7.

## Verified on August 25, 2026 — background-closure release

| Gate | Result | Command or endpoint |
|---|---:|---|
| Python tests | 144 passed | `cd app; python -m pytest -q` |
| Static accessibility checks | 10/10 | `python scripts/check_a11y.py` |
| Executable HTTP demonstration, local | 17/17 | `python scripts/demo_flow.py --url http://127.0.0.1:8041` |
| Executable HTTP demonstration, **live with real Cloud Scheduler tick** | 17/17 | `python scripts/demo_flow.py --url https://cold-clock-109051079423.us-central1.run.app --wait-for-scheduler 240` |
| Foundational safety proof | 8/8 | `GET /api/proof` |
| Adversarial hardening proof | 12/12 | `GET /api/hardening/proof` |
| Live Gemma injection-screen recording | 3/3 | `python scripts/record_injection_screen.py` → `app/fixtures/injection.recording.json` |

### Live unattended closure receipt (deployed revision `cold-clock-00038-zcf`)

Case `cc-3af59be1eafa4ed6a5f8a0f0e13deb02`, started with one `POST /api/demo/unattended` and then left alone:

- Request returned `delivery_dispatched` with a 1-minute sandbox ETA and no `received_at`.
- Live model receipts in the same response: Gemini 3.5 Flash `live-vertex-ai`, 5/5 fields, 0 invented; Gemini Embedding 001 `live: true`, winner `label-storage-evidence`; Gemma 4 `live-vertex-ai`, clean, 503 ms.
- **101 seconds later the case was `resolved` with nobody at the screen.** `background_executions[0]`: kind `courier_status_poll`, outcome `case_closed`, attempt 1, trigger `google-oidc`, identity `agent-wake-scheduler@agentic-fleet-2026.iam.gserviceaccount.com`.
- Last timeline entry: `Background wake agent — Courier confirmed handoff`.
- Wake rows: `courier_status_poll: done`; `receipt_followup: cancelled (case resolved by courier confirmation)`.
- Autonomy proof: 10 trace events, 9 automatic, 1 human authority, 0 unclassified, `background_wake_executions: 1`, `cloud_scheduler_triggered_executions: 1`, `closed_by_background_wake: true`, `operator_continue_clicks: 0`, `proof_integrity: verified`.
- Cloud Run request log: `POST /internal/wakes/scan` returns 200 every minute on the serving revision; an unauthenticated call returns 401.

### Defect found and fixed during this release

The first deploy of the day left the Cloud Scheduler worker returning 401 on every tick. `deploy.sh` re-derived `SCHEDULER_AUDIENCE` from the service's `status.url`, which Cloud Run now reports in its hashed form, while the scheduler job mints its OIDC token for the deterministic project-number URL. The worker now accepts every configured audience (comma-separated), the deploy script sets both forms plus the job's own audience, and it routes traffic to the latest revision so a deploy can no longer be silently masked by an earlier canary pin. Regression test: `tests/test_scheduler_auth.py`.

## Verified locally on August 22, 2026

| Gate | Result | Command or endpoint |
|---|---:|---|
| Python tests | 129 passed | `cd app; python -m pytest tests -q` |
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
- Revision verified after deployment: `cold-clock-00018-28v`.
- `/health`: `firestore`, `gemini-3.5-flash`, `human-only`, transactional wakes, active Cloud Trace, and six-service Google stack inventory.
- Live-stack proof: homepage, CSS, JavaScript, and health inventory returned HTTP 200; the header control was present and the deployment reported `agentic-fleet-2026`.
- Autonomy proof: the deployed event path auto-routed the review packet, a named clinical disposition auto-resumed reservation and dispatch, a durable receipt wake was registered, and one POST to /api/demo/full reached verified closure. The autonomy receipt, stylesheet, and JavaScript each returned HTTP 200.
- Public acceptance: `12/12`; foundational proof: `8/8`; hardening proof: `8/8`; customer landing and OpenAPI documentation: HTTP 200.
- Live custom-flow proof: case `cc-a1946abab29741c7a855fdfdd1185706` preserved the supplied fictional package facts, deduplicated a repeated sensor event, persisted in the case queue, passed named-human replacement review, and reached receipt confirmation. Missing acknowledgement returned HTTP 422.
- Public safety boundary: synthetic-only readiness mode; de-identified intake and global reset both returned HTTP 403.
- Customer-surface check: no judge-specific labels remain; `/judges`, `/judges/architecture`, and their former static assets return HTTP 404. OpenAPI remains HTTP 200 and proof APIs remain 8/8.

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

## 2026-08-22 live release proof

- Cloud Run revision: `cold-clock-00022-6z5` (100% traffic; max instances 1; concurrency 10).
- Final local suite: **129 passed**.
- Live full workflow: case `cc-079cf13efe354425ba86b83457dd289c` resolved in 6.5 seconds.
- Live model receipt: `gemini-3.5-flash`; live semantic routing: `gemini-embedding-001`.
- Executable proof endpoint: **8/8**. Public action trace: **9 events** with an explicit redaction contract.
- `/api/model-evidence` cites the official Vertex AI model documentation and states the test-only replay policy.
- The in-app browser could not connect because the workspace Windows browser helper failed before opening a tab. No visual-browser result is claimed; static UI/accessibility contracts and deployed HTTP behavior were verified.
- Stakeholder outcomes and bonus publication points remain unclaimed pending real consented evidence/public URLs.


## Developer API and cumulative autonomy proof — 2026-08-23

- Final Cloud Run revision: `cold-clock-00029-gfq`, 100% traffic.
- Live external flow: missing key returned HTTP 401; self-service key issuance succeeded; authenticated table-top returned HTTP 201 with `X-RateLimit-Limit: 50` and `X-RateLimit-Remaining: 49`.
- Derived autonomy receipt: 7 automatic trace events, 1 protected pharmacist event, 0 continue clicks; synthetic table-top injection is explicitly disclosed.
- Firestore field audit confirmed digests/fingerprints only: no plaintext key and no raw IP.
- Secret Manager version 1 is pinned, the developer UI and OpenAPI docs returned HTTP 200, and the live health inventory includes Secret Manager.
- The in-dialog runner sent a valid product-specific synthetic payload, returned HTTP 201 with **origin: pilot_input**, displayed the JSON response and remaining quota, and its prominent API Docs button returned HTTP 200.
