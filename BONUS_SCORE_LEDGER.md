# Bonus score ledger

Nothing in this file is a claimed score until its public URL or live receipt is present.

| Rules opportunity | Status | Proof required before claim |
|---|---|---|
| Public build content (+0.2 maximum) | Entrant action pending | Publish `docs/build-story.md` publicly and include the required statement that it was created for entering the All Things Agentic Hackathon. |
| Public social post (+0.2 maximum) | Entrant action pending | Publish `docs/social-post.md` with `#AllThingsAgenticHackathon`; add the public URL here and in the submission form. |
| Additional Google AI model: Gemini Embedding 001 (+0.2) | **Verified live 2026-08-25** | `/api/demo/full` and `/api/demo/unattended` receipts show `semantic_routing.model = gemini-embedding-001`, `live = true`. |
| Additional Google AI model: Gemma 4 (+0.2) | **Verified live 2026-08-25** | `injection_screen.model = gemma-4-26b-a4b-it-maas`, `live = true` in the deployed receipts; graded recording `app/fixtures/injection.recording.json` scored 3/3 (clean label passes, two poisoned labels quarantined). |

Both models are operational, not decorative. Embedding 001 routes verified evidence toward label evidence, qualified review, or accessible fulfillment. Gemma 4 is the second layer of the prompt-injection screen on untrusted package text and can only return verbatim spans to quarantine. Neither has any route to a medication disposition.

Current defensible score: **+0.4**. Defensible maximum after publishing the prepared build content and social post: **+0.8** (the Rules cap model bonuses at +0.6 and content/social at +0.2 each). No Veo or Lyria claim is made because an unrelated model would weaken the product story.
