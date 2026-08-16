# ColdClock: Prize-Quality Build Plan

**Track:** The Taskmaster  
**Product promise:** A refrigerator alarm tells you there is a problem. ColdClock carries a temperature-sensitive medication case to pharmacist-reviewed resolution.  
**Primary user:** A person storing insulin or another refrigerated medicine at home.  
**Decision owner:** A licensed pharmacist or other qualified healthcare professional.  
**Status:** Approved for implementation.

## 1. The precise friction

A power or refrigerator failure creates a time-sensitive evidence and coordination problem. The
patient needs the medicine identity, labeled storage conditions, observed temperatures, excursion
duration, previous excursion history, available supply, professional review, a replacement path,
and delivery. Those facts and actions currently live in disconnected systems.

ColdClock starts from an event, not a chat prompt. It assembles the evidence, routes a structured
case to a human reviewer, and—after approval—coordinates the selected resolution through completion.

## 2. What makes this submission different

Existing work supports sensors, monitoring, excursion assessment, medication management, and
delivery. ColdClock's contribution is the patient-side **resolution loop**:

```text
outage or sensor event
  -> medication and label match
  -> bounded excursion record
  -> pharmacist review request
  -> approved disposition
  -> replacement coordination
  -> delivery and receipt proof
```

The product must never be described as the first medication monitor or the first excursion tool.
The defensible novelty is connecting the fragmented steps while preserving professional authority.

## 3. Research and implementation sources

| Design claim | Source and use |
|---|---|
| Temperature-sensitive drugs may lose potency after prolonged refrigeration loss; patients should seek professional/manufacturer guidance | [FDA, Safe Drug Use After a Natural Disaster](https://www.fda.gov/drugs/emergency-preparedness-drugs/safe-drug-use-after-natural-disaster) — problem framing and safety boundary |
| Insulin must be protected from heat, sunlight, and freezing; switching products should involve a clinician where possible | [CDC, Managing Insulin in an Emergency](https://www.cdc.gov/diabetes/articles/managing-insulin-in-emergency.html) — patient guidance and escalation language |
| Stability varies by formulation, temperature, duration, and evidence quality | [Cochrane review, Thermal stability and storage of human insulin](https://pubmed.ncbi.nlm.nih.gov/37930742/) — reason the agent cannot apply one universal rule |
| Home refrigeration failures caused medicine loss during a prolonged disaster | [Hurricane Maria community study](https://pmc.ncbi.nlm.nih.gov/articles/PMC9664670/) — real-world impact context |
| Continuous home monitoring is feasible but does not itself close the resolution workflow | [QChainMED pilot](https://pmc.ncbi.nlm.nih.gov/articles/PMC13039186/) — prior art and monitoring feasibility |
| Excursion management requires documentation, quarantine, assessment, advice, disposition, replacement, and prevention | [NHS SPS, Managing temperature excursions](https://sps.nhs.uk/articles/managing-temperature-excursions/) — workflow inspiration, not U.S. clinical authority |
| Current structured label data is programmatically available | [openFDA drug-label API](https://open.fda.gov/apis/drug/label/) and [DailyMed web services](https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm) — evidence retrieval |

Every public page must distinguish U.S. public guidance, non-U.S. workflow inspiration, published
research, synthetic demo data, and product-generated estimates.

## 4. End-to-end product flow

1. User creates a synthetic demonstration household and photographs or selects a medicine fixture.
2. Gemini 3.5 Flash transcribes the package and extracts name, strength, form, lot, and label code.
3. Deterministic verification retains only values quoted in the transcription.
4. The evidence agent matches a current structured label and records the source URL and retrieval time.
5. A simulated battery-backed sensor or utility webhook creates a temperature event.
6. The case agent computes observed duration and min/max temperatures without deciding medicine safety.
7. The reviewer agent creates a concise, source-bearing packet and requests human review.
8. The pharmacist portal chooses one bounded disposition: continue per labeled conditions, shorten
   beyond-use window, monitor clinically, replace, or request manufacturer guidance.
9. Only after approval, the fulfillment agent checks synthetic pharmacy inventory and prepares a
   replacement request.
10. The logistics agent books a synthetic courier slot and records delivery evidence.
11. The patient confirms receipt; the system closes the case with an immutable action timeline.

## 5. Safety contract

- ColdClock does not prescribe, diagnose, replace a pharmacist, or independently decide use/discard.
- Unknown identity, missing label evidence, conflicting storage evidence, repeated excursions, or
  unavailable professional review causes a safe stop.
- The interface never labels medicine "safe". It displays "reviewed disposition" and names the reviewer.
- Consequential outbound actions require explicit approval and are sandboxed in the public demo.
- No real patient data is needed; repository fixtures are synthetic.
- Model output is treated as untrusted until quote and schema verification pass.

## 6. Architecture

- FastAPI service packaged for Cloud Run.
- Gemini 3.5 Flash through Vertex AI / Google Gen AI SDK for multimodal package reading.
- Firestore-compatible repository for cases, events, approvals, actions, and audit history.
- Cloud Scheduler-compatible wake scanner for unresolved cases and delivery follow-up.
- OpenTelemetry hooks for Cloud Trace and structured logging.
- Modular roles: Intake, Label Evidence, Excursion Record, Reviewer Packet, Fulfillment, Logistics,
  Verifier. Logical roles are not misrepresented as separate IAM identities.
- Replay mode makes tests and the public demo deterministic and inexpensive.

## 7. Judge and first-user experience

The landing page answers four questions above the fold: what happened, what ColdClock will do, what
it will never decide, and how to run the synthetic case. The console uses a horizontal resolution
timeline on desktop and stacked cards on mobile. Source evidence is one click from every medication
fact. Clinical approval is visually distinct from AI work.

Required interface states:

- calm monitoring state;
- active excursion with time and temperature evidence;
- waiting for pharmacist;
- approved resolution in progress;
- delivered and closed;
- safe stop with actionable next step.

Light and dark modes are equal products, not an inverted afterthought. Both must pass WCAG 2.2 AA.

## 8. Evaluation

- Package extraction accuracy against adjacent ground truth.
- Label-match precision and explicit unknown rate.
- Temperature calculation accuracy.
- Zero autonomous clinical disposition in route and state-machine tests.
- Zero fulfillment actions before approval.
- Idempotent event and order handling.
- Resume after simulated crash.
- Source-link completeness for public factual claims.
- Keyboard, contrast, reduced-motion, responsive, and no-horizontal-scroll checks.
- Executable local and deployed demo flows.

No outcome-reduction claim will be made without a real pilot.

## 9. Four-minute demo spine

1. Show a synthetic insulin package and normal monitoring state.
2. Trigger an outage; temperature begins to rise.
3. Show verified package extraction and structured-label evidence.
4. Open the generated excursion packet; highlight that the agent has made no clinical decision.
5. Approve replacement in the pharmacist view.
6. Watch inventory selection, replacement request, courier booking, and receipt confirmation.
7. Open the immutable action/evidence timeline and Cloud trace proof.
8. End on limitations, evaluation results, and deployment evidence.

## 10. Release gates

- Complete end-to-end workflow with no dead UI controls.
- All tests and executable demo checks green.
- Every factual public claim linked to a source.
- No autonomous clinical decision route exists.
- Honest labels for synthetic connectors, simulated time, and replayed model recordings.
- Public Cloud Run service, Firestore proof, Vertex AI proof, architecture diagram, README,
  differentiation document, validation report, and submission kit.

