---
title: The request has to end before the work does
published: false
description: My agent finished inside the HTTP request that started it, which is not autonomy. Here is what changed when Cloud Scheduler started closing the cases instead.
tags: googlecloud, ai, python, showdev
cover_image:
---

I created this piece of content for the purposes of entering the All Things Agentic Hackathon.

## The thing I got wrong first

I was building an agent for a small, annoying problem: your power goes out, the fridge with your insulin in it gets warm, and the alarm on the sensor is where the help stops. Somebody still has to work out which medicine it was, how long it was warm, reach a pharmacist, arrange a replacement, and confirm it arrived.

My first version did all of that. You clicked a button, and about fifteen seconds later the case was closed. It looked great in a screen recording.

It was not autonomous. It was one HTTP request that happened to do nine things. If you closed the tab halfway through, nothing finished. There was no moment where the system was on its own, because there was no moment where I was not standing there holding it.

That distinction turned out to be the whole project.

## What "on its own" actually requires

The rewrite was simple to describe and annoying to build: **the request must end before the work does.**

So the workflow now stops after dispatching a courier, and writes down what it intends to do next:

```python
def register_followups(case, scheduler) -> list[str]:
    """Register the wakes appropriate to the case's current state."""
    registered = []
    if case["status"] == "awaiting_professional_review":
        _record(case, scheduler.sleep_for(case_id, "review_followup", timedelta(minutes=30)))
        registered.append("review_followup")
    if case["status"] == "delivery_dispatched":
        eta = int((case.get("delivery") or {}).get("eta_minutes") or 0)
        _record(case, scheduler.sleep_for(case_id, "courier_status_poll", timedelta(minutes=eta)))
        _record(case, scheduler.sleep_for(case_id, "receipt_followup", timedelta(minutes=60)))
    return registered
```

Those "wakes" are rows in Firestore. Cloud Scheduler calls a worker every minute with a Google-signed OIDC token. The worker verifies the identity, claims each due wake inside a transaction with a lease, runs an idempotent action, and marks it done. If the action throws, the wake goes back to pending with a bounded retry count and eventually a dead letter, instead of retrying forever.

The result is a page you can close. A minute after a pharmacist records a decision, the case closes itself, and the browser finds out later.

## Three bugs that only appear when nobody is watching

Synchronous code hides a lot. Here is what fell out once the work moved to a background worker.

**The courier that always said yes.** My sandbox courier returned "delivered" whenever the poll fired. That is not a check, it is a timer with extra steps. I rewrote it as a stateful connector with a poll count and an injectable delay. Now "still in transit" causes a bounded re-poll, and a courier that never confirms leaves the case open with a visible hold for a human. No receipt is ever invented.

**Two clocks that disagreed.** A utility publishes an outage with its own timestamp. A household's sensor has its own clock. A baseline reading stamped 110 milliseconds *after* the outage started was being counted as evidence from during the outage, which meant a household whose sensor had gone completely silent looked like it was reporting fine, and never reached its safe stop. The fix was to stop comparing timestamps from different sources and judge by arrival order instead:

```python
# Evidence is judged by arrival order, not by comparing timestamps from different clocks.
outage["readings_at_outage"] = len(case["sensor"]["readings"])
```

**A falsy zero.** For the demo I wanted a courier ETA of zero minutes, meaning "poll on the very next scheduler tick." The dispatch code read `case.get("delivery_eta_minutes") or DEFAULT_ETA`, and `0 or 34` is `34`. Everything passed. The case simply never closed while anyone was watching. Classic, and it only showed up when I timed the live path with a stopwatch instead of trusting the tests.

## Letting a model help without letting it decide

The medicine question, "is this insulin still safe," is not mine to answer and not the model's either. FDA and CDC guidance both point at a pharmacist, and a Cochrane review on insulin thermal stability shows that stability varies by formulation, temperature and duration, which is exactly why a threshold rule would be wrong to automate.

So the rule I designed to is: **the agent acts where a mistake can be undone, and stops where it cannot.**

Reading a label wrong is recoverable, so Gemini reads the package, but a field is only kept if it appears word for word in the model's own transcription. Reserving inventory is recoverable, so that is automatic. Telling somebody their insulin is fine is not recoverable, so a named human owns it and the state machine physically cannot proceed without it.

A Google ADK agent assembles the pharmacist's packet through three read-only tools, and then a plain function checks its homework:

```python
def verify_packet(candidate, truth) -> list[str]:
    """Return the names of fields the model got wrong. Empty means the packet is accepted."""
    rejected = []
    for key in PACKET_FIELDS:
        expected, actual = truth[key], candidate.get(key)
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            if abs(float(expected) - float(actual)) > 1e-9:
                rejected.append(key)
        elif str(actual).strip() != str(expected).strip():
            rejected.append(key)
    question = str(candidate.get("question") or "").strip()
    if "disposition" not in question.lower() or any(t in question.lower() for t in FORBIDDEN_TERMS):
        rejected.append("question")
    return rejected
```

If the agent invents a number, or slips in a sentence implying the medicine is safe, the whole packet is thrown away and a deterministic one is used instead. The workflow never depends on the model being right. Only on it being checkable.

Gemma 4 does something similar for prompt injection on the package label. It may only return spans that exist verbatim in the text, so its output is verifiable rather than trusted, and it has no route to a decision.

## Proving it, instead of claiming it

Every agent demo says "autonomous." I wanted a number that could not be fudged.

Each case emits a receipt derived from the stored timeline: operator clicks after the human decision, background wakes fired, human decisions, and whether the case was closed by a scheduler wake. Then it is signed with HMAC using a key from Secret Manager. Change one field in a copy and the verify endpoint rejects it.

There is a fail-closed detail I like: if a timeline entry has an actor the classifier does not recognise, the proof reports it as unclassified and marks itself invalid, rather than quietly counting it as an agent action. I found that one the hard way when a new background actor made a genuinely autonomous run report `proof_integrity: incomplete`.

## What it looks like now

One click starts a synthetic case. Live models read the package, screen it, and build the packet. It stops with `AI DISPOSITION: NONE`. A pharmacist records a decision. Then you take your hands off the keyboard, and about a minute later the page says:

> Delivered. Closed by a Cloud Scheduler wake, no operator.

with zero operator clicks on a signed receipt.

One utility outage event reaches every monitored household at once, and each one gets judged separately from its own readings: warm goes to a pharmacist, still-in-range keeps being watched, silent sensor stops safely and asks for a person.

## Honest limits

Everything downstream is a labelled sandbox connector. No real pharmacy, courier or insurer. Every person and medicine lot is fictional, the demo clock is simulated and says so on screen, and no pharmacist has reviewed the packet design yet. It demonstrates workflow execution, not clinical benefit, and I have been careful not to claim otherwise anywhere in the project.

## Try it

- Live: https://cold-clock-109051079423.us-central1.run.app
- Code: https://github.com/usv240/cold-clock
- Executable proofs, if you like that sort of thing: `/api/proof` and `/api/hardening/proof`

Built on Cloud Run, Firestore, Cloud Scheduler, Pub/Sub, and Vertex AI with Gemini 3.5 Flash, Gemini Embedding 001 and Gemma 4, using the Google ADK and the Gen AI SDK.

If you take one thing from this: if your agent finishes inside the request that started it, you have written a function. The interesting part starts when the request ends and the work does not.
