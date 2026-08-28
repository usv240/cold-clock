## Inspiration

When the power goes out, a fridge holding insulin sends an alarm. And then nothing happens.

Someone still has to work out exactly which medicine it was, how long it was warm, what the label says about storage, reach a pharmacist, arrange a replacement, and make sure it arrives. The alarm is only the beginning, and every step after it lands on the person having the worst day.

This is not a rare edge case. An estimated [2.1 million people in the United States have diagnosed type 1 diabetes](https://www.cdc.gov/diabetes/php/data-research/index.html) and depend on insulin that must stay refrigerated, and in 2024 the average U.S. electricity customer [lost 11 hours of power](https://www.eia.gov/todayinenergy/detail.php?id=66744), roughly twice the previous decade's annual average. After Hurricane Maria, people [reported having to discard insulin](https://pmc.ncbi.nlm.nih.gov/articles/PMC9664670/) they could not keep cold.

Monitoring products stop at the alert. We wanted an agent that does the work that follows.

## What it does

ColdClock carries a refrigeration failure all the way to a closed case, and stops for exactly one thing.

**It observes.** Gemini 3.5 Flash reads the medicine package. Every field it keeps must appear word for word in the model's own transcription, or it is thrown away. Gemma 4 screens the label text for anything shaped like an instruction, so a printed sentence cannot talk the system into doing something. Gemini Embedding routes the evidence to the right place.

**It prepares the decision, but never makes it.** A Google ADK agent assembles the pharmacist's review packet through three read-only tools, and a verifier compares every value in that packet against what the tools actually returned. An invented number or a "this is safe" sentence throws the whole packet away. The packet shows **AI DISPOSITION: NONE**, and the code makes replacement impossible until a named human records a decision.

The rule we designed to: **the agent acts where a mistake can be undone, and stops where it cannot.** Reading a label wrong is caught and rejected. Reserving inventory can be reversed. Telling someone their insulin is safe cannot be, so a pharmacist owns that, backed by [FDA](https://www.fda.gov/drugs/emergency-preparedness-drugs/safe-drug-use-after-natural-disaster) and [CDC](https://www.cdc.gov/diabetes/articles/managing-insulin-in-emergency.html) guidance, and by a [Cochrane review](https://pubmed.ncbi.nlm.nih.gov/37930742/) showing insulin stability varies by formulation, temperature and time, which is exactly why no threshold rule should be automated.

**Then it finishes on its own.** One human decision automatically reserves matching inventory and books an accessible courier. A durable wake is stored in Firestore. Cloud Scheduler wakes the agent every minute with a signed Google identity; the agent polls the courier, records the handoff, closes the case, and cancels the reminders that are no longer needed. Nobody clicks. The page updates by itself.

**And it proves it.** Every case carries a receipt derived from stored records: operator clicks after the decision, background wakes fired, human decisions, and whether the case was closed by a scheduler wake. The receipt is HMAC-signed; change one number and the verify endpoint rejects it.

**It scales past one fridge.** One utility outage event reaches every monitored home in the area at once, and each home gets its own background watch. Minutes later the agent has reached three different conclusions from three different sets of readings: the warm fridge is routed to a pharmacist, the one still in range keeps being watched, and the one whose sensor went quiet stops safely and asks for a person. Nobody triaged them.

**It is also an API.** Any developer can generate a key with no account and drive the same durable workflow programmatically, with per-key and per-network quotas.

## How we built it

Everything runs on Google Cloud, live, on synthetic data.

- **Cloud Run** hosts one FastAPI service with a typed, bounded state machine. Out-of-order actions return a conflict instead of quietly advancing.
- **Vertex AI** through the **Google Gen AI SDK** for Gemini 3.5 Flash, Gemini Embedding 001, and Gemma 4. Extraction and routing fail closed: if a model is unavailable the workflow stops rather than replaying a recording.
- **Google ADK** for the review-packet agent, with three scoped read-only tools and a post-model verifier, so the model's reasoning is used only where it can be checked.
- **Firestore** for cases and wakes. Cases use optimistic versions, so a stale concurrent write is rejected rather than merged. Wakes are claimed inside transactions with a lease, bounded retries, and a dead-letter path.
- **Cloud Scheduler** calls the background worker every minute with a Google-signed OIDC token. The app verifies audience, issuer and service account; an unauthenticated call gets a 401.
- **Pub/Sub** delivers sensor readings and utility-outage events to the same verified endpoint.
- **Secret Manager** holds the key used to sign receipts, and **Cloud Trace** correlates requests.

Every downstream actor (pharmacy, courier, insurer, sensor, household) is a labelled sandbox connector, and the demo clock is simulated and says so on screen.

## Challenges we ran into

**Finishing a workflow in one request is not autonomy.** Our first version completed the whole story inside a single HTTP call. It looked autonomous and proved nothing. Moving the closure to a Cloud Scheduler wake, and then deriving the proof from persisted records instead of anything the caller asserts, was the real work.

**A courier that always confirms is a timer, not a check.** We rewrote the sandbox courier as a stateful connector. If it reports "still in transit", the agent re-polls a bounded number of times, and if it never confirms, the case stays open with a visible hold. No receipt is ever invented.

**Clocks disagree.** A household's own baseline reading, stamped a few milliseconds after a utility's outage timestamp, was being counted as evidence from during the outage, so a silent sensor never reached its safe stop. The watch now judges readings by arrival order rather than by comparing timestamps from two different clocks.

**Making the model checkable rather than trusted.** Gemma may only return spans that exist verbatim in the text. The ADK agent's packet is compared field by field against its own tools. Neither model can reach a medication decision, so being wrong is caught rather than costly.

## Accomplishments that we're proud of

The moment we can show rather than claim: a pharmacist records their decision, the presenter takes their hands off the mouse, and about a minute later the page reads **"Delivered. Closed by a Cloud Scheduler wake, no operator"** with a signed receipt saying zero operator clicks.

We are also proud of the parts that refuse to act. Missing readings, a reviewer who never answers, matching stock that isn't there, a courier that never confirms, a label that tries to give orders, and a model that invents a number all stop safely. Those aren't slides; twenty of them are executable checks anyone can run against the live service at `/api/hardening/proof`.

And ColdClock is honest about what it is: every person, package, pharmacy and courier is synthetic, and the research is cited with an explicit note of what each source does *not* support.

## What we learned

The valuable behaviour was continuity, not prediction. Nobody needs an AI opinion about whether insulin is still good; they need the twelve boring steps after the alarm to happen.

Autonomy is only believable when it is auditable. A counter that says zero clicks means nothing unless it comes from stored records and cannot be edited, so we derived it from the timeline and signed it.

A small model is most useful when its output is constrained to something checkable. Verbatim spans and verified fields make Gemma and the ADK agent genuinely helpful without letting either near a decision.

## What's next for ColdClock

Real sensor gateways and utility feeds on the Pub/Sub topics that already exist. A private, identity-controlled deployment for authorized de-identified data, since the public service is synthetic-only by design. Pharmacist review of the packet, the disposition vocabulary and the safe stops, which no clinician has evaluated yet. More medication fixtures recorded and graded against their real labels.

And the wider pattern: when an alarm needs a professional decision, the agent can handle the work around that decision. That shape is not specific to one refrigerator.

**We make no clinical claim.** ColdClock demonstrates workflow execution on synthetic data. It has not been shown to improve any health outcome.
