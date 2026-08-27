# ColdClock — 4-minute demo script (one take)

Target runtime **3:35–3:50**. Only the first four minutes are judged. Spoken lines are in quotes; keep them, drop nothing else. Talk slowly; the app does the work.

## Before you press record (10 minutes)

1. Run `python scripts/browser_check.py --url https://cold-clock-109051079423.us-central1.run.app --wait 240` — it must print `7/7`. This also warms the instance.
2. Browser tabs, left to right, all logged in and already loaded:
   - **Tab 1** the app: `https://cold-clock-109051079423.us-central1.run.app` (light theme is the default; scrolled to the operations workspace, window wide enough that the autonomy rail is one line).
   - **Tab 2** Cloud Run → service `cold-clock` → **Revisions** (shows the serving revision and 100 % traffic).
   - **Tab 3** Cloud Scheduler → job `cold-clock-wake-scan` (every minute, last run status).
   - **Tab 4** Firestore → collection `cold_clock_wakes` (any document open).
   - **Tab 5** Cloud Run → service `cold-clock` → **Logs**, filtered to `/internal/wakes/scan`.
3. Close every other tab. No third-party sites, logos or brand pages on screen at any point (the Rules forbid it). Do not open DailyMed/FDA pages.
4. Record screen + mic in one continuous take. No cuts. If a step misfires, say what you see and continue — judges score honesty over polish.

## The take

### 0:00–0:25 — the friction (Tab 1, top of the app)

"When the power goes out, a home fridge holding insulin sends an alarm — and then nothing happens. Someone still has to figure out exactly which medicine and lot, how long it was out of range, find the current storage guidance, reach a pharmacist, arrange a replacement, and prove it arrived. Monitoring products stop at the alert. ColdClock starts there, and finishes the job while nobody is watching. Everything you'll see is synthetic and runs on Google Cloud. One thing it will never do is decide whether the medicine is safe — a pharmacist does."

### 0:25–0:50 — one click (Tab 1, click **Run unattended**)

While it runs (~15 s), say:

"One click. Gemini 3.5 Flash on Vertex AI is reading the package with exact-quote grounding — every field it keeps must appear word-for-word in its own transcription. Gemma 4 screens the label text for injected instructions. Gemini Embedding routes the evidence. And a Google ADK agent assembles the pharmacist's packet through three read-only tools, with a verifier checking every value against what the tools returned."

When it stops: point at the status **Waiting for pharmacist**. Click the **Medicine evidence** tab — point at the verified fields and the green injection-screen line. Click **Review packet** — point at **AI DISPOSITION: NONE · HUMAN DECISION REQUIRED** and the **ADK agent packet accepted · 3 scoped tool calls · 6 values verified** card.

"It stopped here on purpose. This is the only decision the system refuses to make."

### 0:50–1:15 — the one human decision (Tab 1)

Click **Record human disposition**. Type a name and credential, choose **Replace**, type one sentence of rationale, submit.

"I'm the pharmacist for this demo. That was the only decision a person makes."

Watch the journey rail: **Replacement reserved** and **Accessible delivery** tick by themselves. Point at the **Durable wakes** panel: *Poll sandbox courier at ETA · pending*, and the line *Cloud Scheduler scanned Ns ago (verified Google OIDC)*. Point at the autonomy rail: **0 continue clicks**.

"From here, nobody clicks. A durable wake is registered in Firestore. Cloud Scheduler calls the worker every minute with a signed identity token; at the ETA the worker polls the courier, records the handoff and closes the case. Let me show you that running on Google Cloud while it happens."

Take your hands off the mouse for one visible second.

### 1:15–2:40 — proof on Google Cloud (Tabs 2 → 5, ~20 s each)

- **Tab 2 (Cloud Run revisions):** "This is the service — one Cloud Run container, the revision that's serving, 100 % of traffic."
- **Tab 3 (Cloud Scheduler):** "The job that makes the agent autonomous — every minute, with an OIDC token from a dedicated service account. The app verifies audience, issuer and identity; an unauthenticated call gets a 401."
- **Tab 4 (Firestore `cold_clock_wakes`):** refresh; find the newest `courier_status_poll` document. "Here is the wake itself in Firestore — claimed in a transaction with a lease, bounded retries, dead letters. Watch the status." (Refresh once more if it's still `pending`; it will read `done` within about a minute.)
- **Tab 5 (Cloud Run logs):** "And the scheduler's calls landing on the worker, 200 every minute."

### 2:40–3:05 — it finished by itself (Tab 1)

Switch back. The page will already have updated.

"No refresh, no click. The case is **resolved**. The autonomy rail reads *Closed by a Cloud Scheduler wake — no operator*, background wakes *1 fired · closed case*. The timeline's last entry is the background agent: *Courier confirmed handoff*. The receipt reminder cancelled itself — marked, never deleted."

Click **Open signed autonomy proof** (timeline footer). Point at `closed_by_background_wake: true`, `cloud_scheduler_triggered_executions: 1`, `operator_continue_clicks: 0`, `proof_integrity: verified`, and `signature`.

"This receipt is derived from persisted state and HMAC-signed — edit one field and the verify endpoint rejects it."

### 3:05–3:25 — scale and failure, in one breath (Tab 1)

Click **Simulate grid outage**.

"Real outages aren't one household. One utility event fans out to every enrolled case in the grid area — each gets its own background watch and is judged from its own readings: excursion routed to review, in range kept watching, silent sensor becomes a safe stop. And every failure we could think of is an executable proof: missing evidence, an unavailable reviewer, a courier that never confirms, injected label text, a model that invents a number — all stop safely. Twenty out of twenty, live."

(Optional if time: open `/api/hardening/proof` in Tab 1 and show `"passed": 20, "total": 20`.)

### 3:25–3:45 — close (Tab 1, scroll to top or show README architecture)

"ColdClock is an event-to-resolution agent: Gemini, Gemma and an ADK agent for evidence; Firestore for state; Cloud Scheduler and Pub/Sub for background execution; a human for the one decision that must stay human; and a signed receipt for everything else. All people, packages and connectors are synthetic, the demo clock is simulated and says so, and no clinical claim is made. The repo, diagram, and reproducible proofs are linked below. Thank you."

Stop recording.

## After recording

- Title the video "ColdClock — All Things Agentic Hackathon". Description: hosted URL, repo URL, and the sentence "I created this piece of content for the purposes of entering the All Things Agentic Hackathon." (that sentence also qualifies the video for the content bonus).
- Publish **public** (not unlisted) on YouTube or Vimeo, English audio; add auto-captions.
- Paste the link into the Devpost form and into `submission-manifest.json` → `video_url`.

## If something goes wrong mid-take

- **Run unattended takes longer than 30 s:** keep talking through the model list; it's a cold start, it will land.
- **Case hasn't closed when you return at 2:40:** say "the scheduler ticks once a minute" and show the Firestore wake document again; go to the outage beat and come back — it will be closed. Do not click *Confirm household receipt*.
- **Any 503 "live model evidence unavailable":** say "the workflow fails closed rather than replaying a recording — that's by design," click **Run unattended** again.
