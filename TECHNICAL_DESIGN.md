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
recording came from an explicit Vertex AI call and passed `4/4` adjacent truth checks; tests and the
tests replay it deterministically; the deployed full workflow calls it live and fails closed.

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

## Deployment

- `Dockerfile`: non-root Python 3.12 runtime.
- `deploy.sh`: Cloud Run source deployment to `us-central1`, unauthenticated judging access, and
  Firestore mode.
- `/health`: identifies project, persistence, models, live fail-closed mode, synthetic data, and human-only
  clinical authority.
- `/api/proof`: executable safety and action assertions.
- `/api/conformance`: contest requirement mapping and limitations.

Cloud Trace dependencies are declared. Trace initialization and durable scheduled follow-up remain
release work and must not be claimed until implemented and verified in the deployment.

## UI

The product has one customer-facing operations route. Technical architecture and executable proof remain in the README and API. The interface provides equal light and dark themes,
responsive layouts, keyboard focus, reduced-motion handling, text-labelled status, evidence links,
and an `aria-live` activity stream. The interactive console calls the same HTTP state machine used
by the acceptance script.

## Explicitly absent

- autonomous medical advice or a safety/discard verdict;
- production insurer, pharmacy, utility, sensor, or courier integration;
- real patient data;
- a completed live Gemini recording;
- pharmacist field validation;
- validated outcome improvement;
- a completed live Gemini recording and external expert validation.





