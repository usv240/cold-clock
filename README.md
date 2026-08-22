# ColdClock

> When refrigeration fails, the alarm is only step one.

ColdClock is an event-driven agent that carries a temperature-sensitive medication case from a
power or refrigerator failure to **pharmacist-reviewed resolution**. It assembles observed evidence,
routes a bounded review packet, and—only after a qualified human decision—coordinates a synthetic
replacement through delivery and receipt.

**Hackathon track:** The Taskmaster  
**Google model:** Gemini 3.5 Flash through Vertex AI / Google Gen AI SDK  
**Google Cloud:** Cloud Run deployment package plus Firestore-compatible persistence  
**Public-data policy:** The demo uses fictional people, medicine lot, pharmacy, coverage plan,
courier, reviewer, and sensor events.

## Live stack proof

The header's **Live stack** control reads `/health` at runtime. It turns green only on a healthy non-local deployment; hover, click, or keyboard focus reveals the services actually used: Gemini 3.5 Flash on Vertex AI, Google Gen AI SDK, Cloud Run, Firestore, Cloud Scheduler, and Cloud Trace. The panel links to the same machine-readable evidence.

## Autonomy contract and design identity

POST /api/demo/full completes the synthetic outage-to-receipt story in one server request. In the input-driven path, a sensor excursion automatically verifies and routes the reviewer packet; the single qualified disposition automatically resumes reservation, dispatch, and durable receipt follow-up. ColdClock stops only for the clinical authority it cannot own and for real receipt evidence. The UI is intentionally an ambient clinical instrument: cool telemetry color, rounded monitoring surfaces, and a live autonomy rail.

## From reproducible proof to operational pilot

The public Cloud Run workspace is intentionally signup-free for hackathon evaluation and accepts synthetic inputs only. It supports multiple durable cases and typed event ingestion without inviting real patient information. New cases use complete random UUIDs, destructive global reset is disabled, and internal scheduler workers remain OIDC-authenticated. A real-data deployment would be a separate protected partner environment.

The deterministic sample remains available because reviewers and maintainers need a repeatable safety
case. It is no longer the only product path. The running application also provides a persistent
multi-case queue and an input-driven pilot API at `/api/pilot`:

- create a synthetic monitored case from supplied package facts on the public service;
- retain fields only when they appear verbatim in the supplied transcription;
- attach the authoritative label URL, exact storage excerpt, and human-configured monitoring range;
- ingest real event-shaped sensor payloads exactly once by device event ID;
- calculate observed duration and temperature range without producing a medication disposition;
- require a named qualified reviewer to enter the disposition and independent rationale;
- preserve every case in Firestore instead of clearing global state when the page opens.

`GET /api/pilot/readiness` states what works and what remains before PHI or clinical deployment.
The public service is currently a **synthetic operational pilot**, not production clinical software. An authorized de-identified mode is disabled by default and belongs only in a private, identity-controlled deployment. See the
[startup-readiness audit](STARTUP_READINESS.md) for the identity, compliance,
integration, validation, and operating controls still required.
## The one-sentence distinction

A monitoring product tells someone that the temperature changed. ColdClock executes the fragmented
work that follows while keeping medication-use authority with a qualified professional.

## Why this problem is credible

- FDA disaster guidance explains that extended refrigeration loss can affect temperature-sensitive
  medicine and directs patients to pharmacists, healthcare providers, or manufacturers for product-
  specific guidance: [FDA, Safe Drug Use After a Natural Disaster](https://www.fda.gov/drugs/emergency-preparedness-drugs/safe-drug-use-after-natural-disaster).
- CDC provides emergency insulin-storage precautions and advises clinical involvement when switching
  insulin products: [CDC, Managing Insulin in an Emergency](https://www.cdc.gov/diabetes/articles/managing-insulin-in-emergency.html).
- A Cochrane review found that stability evidence and recommendations vary by formulation,
  temperature, time, and evidence source: [Thermal stability and storage of human insulin](https://pubmed.ncbi.nlm.nih.gov/37930742/).
- Communities affected by Hurricane Maria reported difficulty refrigerating medicine and disposal
  of insulin during extended outages: [community impact study](https://pmc.ncbi.nlm.nih.gov/articles/PMC9664670/).
- The QChainMED pilot demonstrates the feasibility of continuous home monitoring and gives us a
  clear prior-art boundary: [QChainMED pilot](https://pmc.ncbi.nlm.nih.gov/articles/PMC13039186/).

These sources support the problem and design choices. They do **not** validate ColdClock or prove
that it improves clinical outcomes.

## What the running workflow does

```text
synthetic package + normal sensor
              |
              v
      power / sensor event
              |
              v
 verified package + label + temperature evidence
              |
              v
     named human pharmacist gate
              |
      approved disposition?
        /             \
      no               yes: replace
  safe stop                 |
                            v
              sandbox inventory reservation
                            |
                            v
                accessible courier dispatch
                            |
                            v
                     receipt proof
```

The public demonstration implements seven visible workflow states:

1. `monitoring`
2. `excursion_detected`
3. `awaiting_professional_review`
4. `replacement_approved`
5. `fulfillment_prepared`
6. `delivery_dispatched`
7. `resolved`

Out-of-order actions return HTTP `409`. No route exists to prescribe, diagnose, declare medicine
safe, or tell a patient to discard it.

## Safety contract

- The model reads packages and assembles evidence. It never chooses the medication disposition.
- Fulfillment is impossible until a supported disposition is recorded by a named human reviewer.
- Unsupported, missing, or conflicting evidence causes a stop rather than an inferred answer.
- Every package value retained by the reader has an exact quote in the model's transcription.
- The public pharmacy, insurance, courier, patient, reviewer, sensor, and utility connectors are
  explicitly synthetic and sandboxed.
- No endpoint claims clinical approval, prescription, production integration, or outcome benefit.

## Architecture

The customer-facing application intentionally omits rubric language, test counts, infrastructure pages, and judge-only navigation. Technical and submission reviewers can verify the same claims through the architecture below, the API documentation at `/docs`, the executable proof endpoints, `TECHNICAL_DESIGN.md`, and `VALIDATION_EVIDENCE.md`.

![ColdClock architecture](docs/architecture.svg)

| Layer | Running implementation |
|---|---|
| Interface | Responsive, keyboard-operable light/dark operations workspace |
| API | FastAPI with a typed, bounded state-transition contract |
| Agent logic | Package evidence, excursion evidence, review packet, fulfillment, logistics, and audit roles |
| Model | Gemini 3.5 Flash package reader; deterministic replay is used by tests and public rehearsal |
| Persistence | Memory locally; Firestore adapter in Cloud deployment mode |
| Compute | Dockerized Cloud Run service |
| Evidence | DailyMed structured label URL, observed sensor fixture, named human approval, receipt proof |

The roles are modular application boundaries. This repository does not claim that every logical
role executes under a separate IAM identity.

## Repository map

```text
cold-clock/
  PLAN.md                         research, differentiation, safety, UX and release plan
  README.md                       public technical and product guide
  TECHNICAL_DESIGN.md             as-built architecture and boundaries
  PROJECT_DIFFERENTIATION.md      direct prior-art comparison
  VALIDATION_EVIDENCE.md          measured checks and remaining validation
  SUBMISSION_KIT.md               Devpost copy and video spine
  docs/architecture.svg           technical architecture diagram
  app/
    cold_clock/
      workflow.py                 safety-bounded state machine
      reader.py                   live Vertex + replay package reader
      store.py                    memory and Firestore adapters
    service/
      main.py                     Cloud Run/FastAPI entry point
      routes.py                   public API, proof and conformance endpoints
    fixtures/                     adjacent synthetic recording and truth
    scripts/
      demo_flow.py                executable 12-step acceptance path
      check_a11y.py               static accessibility gate
      record_package.py           explicit live-model recording and grading command
    tests/                         domain, API, reader, claims, UI and safety tests
    web/                           customer-facing product experience
    Dockerfile
    deploy.sh
```

## Run locally

```powershell
cd app
python -m pip install -r requirements.txt
python -m uvicorn service.main:app --host 127.0.0.1 --port 8000
```

Open:

- Product: `http://127.0.0.1:8000/`
- API: `http://127.0.0.1:8000/docs`
- Executable safety proof: `http://127.0.0.1:8000/api/proof`
- Adversarial hardening proof: `http://127.0.0.1:8000/api/hardening/proof`

## Verify

```powershell
cd app
python -m pytest -q
python scripts/check_a11y.py
python scripts/demo_flow.py --url http://127.0.0.1:8000
```

Current local baseline on August 16, 2026:

- `111 passed`
- `10/10` static accessibility checks
- `12/12` executable HTTP acceptance checks
- `8/8` foundational safety proof and `8/8` adversarial hardening proof

Those counts must be rerun after any code or copy change.

## Gemini recording policy

The adjacent recording was produced by a live Vertex AI Gemini 3.5 Flash call on the synthetic PNG
fixture and matched `4/4` exact expected fields. Every retained field has a verbatim transcription
quote. The deterministic public rehearsal replays that measured recording without spending tokens.

To repeat the recording:

```powershell
$env:GOOGLE_CLOUD_PROJECT="your-project"
python scripts/record_package.py --image web/package-fixture.png
```

The script calls Gemini 3.5 Flash explicitly, validates every quote, grades extracted values against
`fixtures/package.truth.json`, and overwrites the recording only after a successful response. The
resulting accuracy may be published only after reviewing the generated report.

## Deploy to Google Cloud

```bash
cd app
export GOOGLE_CLOUD_PROJECT="your-project"
./deploy.sh
```

Deployment enables Firestore through `USE_FIRESTORE=true`. Before recording the submission video:

1. Confirm `/health` shows the intended Google Cloud project and `firestore` persistence.
2. Run the executable demo against the public `.run.app` URL.
3. Capture the Cloud Run revision and Vertex AI evidence.
4. Confirm public unauthenticated access from a clean browser.
5. Keep every sandbox and replay label visible.

## Research ledger

| Source | What it supports | What it does not support |
|---|---|---|
| [FDA disaster guidance](https://www.fda.gov/drugs/emergency-preparedness-drugs/safe-drug-use-after-natural-disaster) | Temperature-sensitive medicine problem and professional escalation | ColdClock efficacy or a product-specific disposition |
| [CDC insulin guidance](https://www.cdc.gov/diabetes/articles/managing-insulin-in-emergency.html) | Emergency precautions and clinical involvement | A universal discard threshold |
| [Cochrane review](https://pubmed.ncbi.nlm.nih.gov/37930742/) | Evidence variability and uncertainty | Automated clinical decision-making |
| [Hurricane Maria study](https://pmc.ncbi.nlm.nih.gov/articles/PMC9664670/) | Real access and refrigeration disruption | A current prevalence estimate |
| [QChainMED pilot](https://pmc.ncbi.nlm.nih.gov/articles/PMC13039186/) | Home-monitoring feasibility and prior art | Full replacement coordination |
| [NHS SPS excursion workflow](https://sps.nhs.uk/articles/managing-temperature-excursions/) | Professional workflow inspiration | U.S. regulatory authority or patient self-assessment |
| [DailyMed fixture label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?audience=consumer&setid=72cfe377-52f6-0348-fc71-5d4ac1992ffb) | Current fixture-specific storage evidence | The review disposition for this synthetic event |

## Known limitations and next validation

- One synthetic medicine fixture does not establish general medication coverage.
- Live structured-label retrieval still needs caching, version checks, and failure-mode testing.
- A pharmacist must review the packet, terminology, dispositions, and safe-stop behavior.
- Real pharmacy, coverage, and delivery integrations require contracts and authorization.
- Accessibility still requires rendered browser, keyboard, and assistive-technology review in
  addition to the static gate.
- No clinical, economic, or public-health outcome claim is made.

## Non-endorsement

ColdClock is an independent hackathon prototype. The FDA, CDC, NIH/NLM, DailyMed, NHS, source
authors, medication manufacturers, pharmacies, insurers, and couriers do not endorse it.

## August 16 hardening

ColdClock now includes transactional Firestore wake claims, a persistent simulated demo clock, bounded retry/dead-letter behavior, Cloud Trace correlation, and explicit recovery paths for missing sensor history, unavailable review, unavailable matching stock, and courier failure. The API exposes both executable proof suites. These controls strengthen execution evidence; they do not establish clinical effectiveness.

## Findings and learnings

- The most valuable behavior is continuity across evidence, authority, inventory, accessibility and receipt, not a temperature prediction.
- Exact-quote extraction is useful only when rejected fields stay visible and incomplete history becomes a safe stop.
- Durable action needs deterministic registration, transactional claiming and idempotent action records.
- This validates one synthetic package workflow, not medication coverage or clinical benefit.

## Originality and reused-code disclosure

ColdClock's domain workflow, UI, fixtures, evaluation, failure laboratory, research and submission materials were created for this contest-period submission. Generic clock, wake, observability, quarantine and verifier primitives were adapted from the entrant's Day Three contest-period production spine. They are disclosed in app/spine/__init__.py and independently tested here.

## Automated background execution

The deployed cold-clock-wake-scan Cloud Scheduler job calls the internal wake worker every minute with a Google-signed OIDC token from the dedicated agent-wake-scheduler service account. The application verifies audience, issuer, email and email verification before scanning. Unauthenticated calls return HTTP 401. The worker claims Firestore wakes transactionally, executes idempotent actions, bounds retries and retains dead letters. Reproduce or update the job with app/infra/provision_scheduler.ps1 after deployment.

