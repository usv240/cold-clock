# ColdClock: the work after the refrigerator alarm

I created this piece of content for the purposes of entering the All Things Agentic Hackathon.

Most cold-chain tools end at an alert. ColdClock begins there. It turns a synthetic home medicine excursion into a verified evidence packet, stops at a named pharmacist decision, and only then coordinates sandbox replacement and accessible delivery.

The part I am proudest of is what happens after dispatch. Nobody clicks. A durable wake is registered in Firestore with a deterministic id; Cloud Scheduler calls the worker every minute with a Google-signed OIDC token; the worker claims the wake in a transaction, polls the sandbox courier at the ETA, records the handoff, resolves the case, and cancels the now-pointless reminder (marked, never deleted). The UI just updates. The autonomy proof is derived from the persisted trace, so it can say `closed_by_background_wake: true` and `operator_continue_clicks: 0` without trusting the caller.

The difficult engineering was failure behaviour: missing temperature history produces no invented reading; an unavailable reviewer preserves the clinical gate; unavailable stock produces no substitution; a courier failure lets a named human choose recovery; and instruction-shaped text on a package is quarantined by a pattern layer plus Gemma 4 before it can reach routing. Gemma may only return verbatim spans that exist in the text, which keeps a small model useful and out of every decision. Gemini 3.5 Flash reads the package with exact-quote grounding, Gemini Embedding 001 routes the evidence, Firestore persists the case with optimistic versions, and Cloud Trace correlates requests.

The public demo proves execution, not clinical outcomes. Every person, lot, pharmacy, and courier is synthetic. A qualified professional remains the only medication-disposition authority.

Try it: https://cold-clock-109051079423.us-central1.run.app — click **Run unattended**, then watch the durable-wakes panel.
