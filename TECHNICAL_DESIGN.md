# ColdClock: As-Built Technical Design

## Runtime and state

ColdClock is one FastAPI application packaged for Cloud Run. Local mode uses an in-memory copy-on-
read store. Deployment mode uses `cold_clock_cases` in Firestore. Each case is a structured state
document with package evidence, observed temperatures, review state, fulfillment state, delivery
state, and an ordered action timeline.

The state machine is deliberately narrow. `prepare_fulfillment` succeeds only when the case is
`replacement_approved` and the named human decision is `replace`. Delivery requires prepared
fulfillment, and receipt requires dispatched delivery. Invalid ordering raises a typed conflict and
cannot silently advance state.

## Model path

`cold_clock/reader.py` implements transcription-first package reading through Gemini 3.5 Flash at
the Vertex AI global endpoint. The JSON schema permits only five fields. A field is retained only
when its nonempty quote occurs in the model's own transcription and confidence is in `[0, 1]`.

Replay and live recording are separate classes. Tests never spend model tokens. The committed
recording came from an explicit Vertex AI call and passed `4/4` adjacent truth checks; tests replay
it deterministically; the deployed workflow calls it live and fails closed.

Two more models run live in the deployed workflow. `spine/semantic_routing.py` uses Gemini
Embedding 001 to rank the transcription against three operational focuses; the winner is a routing
hint, never a decision. `cold_clock/injection_screen.py` runs a deterministic pattern scan and then
asks Gemma 4 (`gemma-4-26b-a4b-it-maas`, Vertex AI Model-as-a-Service, `global`) for verbatim
instruction-shaped spans; each returned span must occur in the text or it is ignored, and every
accepted span is replaced with a visible `[quarantined]` marker before the text is embedded. If the
Gemma call fails the receipt reports `live: false` and the pattern layer stands alone.

## Review-packet agent (Google ADK)

`cold_clock/packet_agent.py` builds an ADK `LlmAgent` on Gemini 3.5 Flash per review request. Its
only view of the case is three read-only closures registered as tools: verified package fields,
the excursion observation, and the label excerpt. Tool calls are recorded in order. The agent's
JSON is verified field by field against the deterministic packet (numeric tolerance 1e-9, exact
strings); a question shorter than ten characters, without the word "disposition", or containing a
safety or discard claim is rejected. Any rejection, a skipped tool, a timeout, or an exception
routes the deterministic packet instead and records why in `packet_agent`. The agent therefore adds
a checkable reasoning step without ever becoming a point of failure or authority.

## Event ingress and fan-out (Pub/Sub)

`service/events_routes.py` receives Pub/Sub push deliveries for two topics through the same OIDC
verifier as the scheduler worker. Sensor events reuse the idempotent pilot ingestion path. A utility
event is fanned out by `cold_clock/outage.py` to every monitoring case in its service area: each
case records the outage as external evidence and gets an `outage_watch` wake (deterministic id per
attempt). When the wake fires, the worker judges the case from readings since the outage — an
excursion is recorded and routed, in-range readings keep a bounded watch (three rechecks), and a
silent sensor becomes the existing incomplete-evidence safe stop. Malformed or unknown messages are
acknowledged with a recorded reason rather than retried forever.

## Signed receipts

`spine/receipt_signing.py` signs the derived autonomy proof with HMAC-SHA256 over canonical JSON,
keyed by the Secret Manager pepper. `POST /api/receipts/verify` recomputes the signature so a copied
receipt can be checked without trusting whoever holds it.

## Background execution

Every path that advances a case calls `cold_clock/followups.py`, which registers durable wakes
idempotently by `(case, kind)`: `review_followup` thirty minutes after routing, and after dispatch
both `courier_status_poll` (due at the sandbox courier ETA) and `receipt_followup` (sixty minutes).
A Cloud Scheduler job calls `POST /internal/wakes/scan` every minute with a Google-signed OIDC
token; `spine/scheduler_auth.py` verifies audience, issuer, and the dedicated service-account
email before anything is dispatched. `spine/wake.py` claims each due wake in a Firestore
transaction with a ninety-second lease, retries a failing handler up to five times, and dead-letters
after that. `cold_clock/wake_actions.py` executes the action idempotently by wake id: the courier
poll records the sandbox handoff, resolves the case, and cancels the now-pointless receipt reminder
(marked, never deleted); the reminders only surface stalls and never contact anyone. Each execution
is appended to the case's `background_executions` with the verified trigger identity, and the
autonomy proof derives `closed_by_background_wake` and `cloud_scheduler_triggered_executions` from
that record rather than from anything the caller asserts.

The clock is injected (`spine/clock.py`). Production and demo share one persisted, forward-only
simulated clock in Firestore so a four-minute recording can reach a thirty-four-minute ETA; the UI
labels it as simulated, and advancing it never dispatches — the next scheduler scan does.

## Evidence and authority

The label record retains source title, URL, retrieval date, jurisdiction, a short source excerpt,
and a bounded interpretation. The code does not convert the excursion into a clinical outcome.
The review packet exposes the observed duration and maximum, package-verification count, opened
date, and source. A qualified human selects one of five bounded dispositions.

The allowed disposition list constrains reviewer input; it does not authorize AI to select a value.
The public demo chooses `replace` through a clearly named synthetic pharmacist interaction.

## External actions

Pharmacy inventory, coverage, courier, reviewer, household, utility, and sensor actors are sandbox
fixtures. Their state changes are real application writes but not external production integrations.
The interface, API, README, and conformance endpoint state this boundary.

The sandbox courier is deliberately stateful so the background poll is a check, not a timer:
dispatch writes a `courier_job` record (`in_transit`, poll count, injectable delay, history);
every `courier_status_poll` asks that record and appends what it reported. A delay makes the job
answer `in_transit`, which re-arms the poll with a deterministic per-attempt wake id at most three
times; a job that never confirms leaves the case open with a visible hold and the sixty-minute
receipt reminder still standing. Only a reported handoff produces a receipt.

Listing is bounded and ordered (`opened_at` descending, sixty rows) and outage fan-out queries by
`service_area`, so the public store can grow without slowing the queue or the fan-out.

## Deployment

- `Dockerfile`: non-root Python 3.12 runtime.
- `deploy.sh`: Cloud Run source deployment to `us-central1`, unauthenticated judging access, and
  Firestore mode.
- `infra/provision_scheduler.ps1`: the every-minute OIDC Cloud Scheduler job.
- `/health`: identifies project, persistence, models, live fail-closed mode, background execution,
  synthetic data, and human-only clinical authority.
- `/api/proof`: executable safety and action assertions (8).
- `/api/hardening/proof`: failure-path, wake, background-closure and quarantine assertions (12).
- `/api/conformance`: contest requirement mapping and limitations.

Cloud Trace is initialised at startup and every response carries `x-agent-trace-id`; the deployed
`/health` reports `tracing.active: true`.

## UI

The product has one customer-facing operations route. Technical architecture and executable proof remain in the README and API. The interface provides equal light and dark themes,
responsive layouts, keyboard focus, reduced-motion handling, text-labelled status, evidence links,
and an `aria-live` activity stream. The interactive console calls the same HTTP state machine used
by the acceptance script.

## Explicitly absent

- autonomous medical advice or a safety/discard verdict;
- production insurer, pharmacy, utility, sensor, or courier integration;
- real patient data;
- pharmacist field validation;
- validated outcome improvement;
- external expert validation.





