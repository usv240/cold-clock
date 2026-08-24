# Release audit — 2026-08-22

This release closes the “simulation-only” and proof-clarity gaps without overstating validation.

- `POST /api/demo/full` performs live, fail-closed Gemini 3.5 Flash package extraction in deployed mode.
- Gemini Embedding 001 routes verified evidence to the next operational focus; it has no medication authority.
- The one-request server workflow runs outage detection, review routing, approved replacement reservation, accessible dispatch, and receipt closure. It stops at the pharmacist decision.
- Every case exposes `/api/cases/{case_id}/trace`, a structured action receipt that excludes prompts, hidden reasoning, credentials, personal data, and stack traces.
- Firestore-backed state, transactional wakes, bounded retry/dead-letter behavior, Cloud Trace, API contracts, and a public synthetic sandbox make the product usable beyond a scripted UI.
- Bonus content and social drafts are ready, but their points remain unclaimed until the entrant publishes public URLs.
- Stakeholder validation remains unclaimed; use `EXTERNAL_VALIDATION_PROTOCOL.md` and record only real, consented evidence.

The remaining Stage 1 blocker is entrant-owned: attach a public, narrated, under-four-minute YouTube or Vimeo demo URL before submission.

## 2026-08-24 production-hardening addendum

- Revision `cold-clock-fs1` serves 100% of traffic.
- Fresh public checks: functional proof 8/8, hardening proof 8/8, live Gemini and Embedding 001, verified autonomy, zero unclassified actors, and zero continuation clicks.
- Primary cases now use Firestore transactions with optimistic `record_version`; stale writes return a retryable HTTP 409.
- The dependency set is pinned to the exact previously verified Firestore/API Core boundary after a zero-traffic canary exposed and prevented a floating-client regression.
- Cloud Scheduler is enabled with OIDC service identity and a successful post-promotion status.
- Local release suite: 132 passing tests.

External stakeholder outcomes, the public video, public build-content URL, and social-post URL remain unclaimed entrant actions.
