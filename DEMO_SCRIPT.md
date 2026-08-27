# ColdClock demo script (one take, under 4 minutes)

Plain words. Short lines. The app does the work; you point and speak.
Target 3:30. Only the first four minutes are judged.

## Setup (10 minutes before recording)

1. Run: `python scripts/browser_check.py --url https://cold-clock-109051079423.us-central1.run.app --wait 240`
   It must print `7/7`. This also warms the service.
2. Open five tabs, in this order, all loaded:
   1. The app (light theme, scrolled to the workspace, wide window).
   2. Cloud Run, service `cold-clock`, Revisions tab.
   3. Cloud Scheduler, job `cold-clock-wake-scan`.
   4. Firestore, collection `cold_clock_wakes`.
   5. Cloud Run, service `cold-clock`, Logs, filtered to `/internal/wakes/scan`.
3. Close everything else. No other websites or logos on screen.
4. One continuous recording, screen plus voice. If something misfires, say what you see and keep going.

## The take

### 0:00 to 0:20. The problem. (Tab 1)

"When the power goes out, a fridge with insulin in it sends an alarm. And then nothing happens.
Someone still has to work out which medicine it was, how long it was warm, call a pharmacist, get a replacement, and make sure it arrives.
Today, the alarm is only the beginning. Someone still has to coordinate everything that comes next.
ColdClock does that work by itself. It stops for one thing: the decision that belongs to a pharmacist."

### 0:20 to 0:45. One click. (Tab 1, press Run unattended)

While it runs, say:

"One click. ColdClock reads the medicine package, checks the storage evidence, and builds everything a pharmacist needs to review the case.
Gemini reads the package. Gemma screens the label for hidden instructions. And a Google ADK agent builds the review packet from read-only evidence. Every value is checked against its source."

When it stops, click the **Review packet** tab. Point at **AI DISPOSITION: NONE** and at **ADK agent packet accepted, 6 values verified**.

"It stopped on purpose. The system will not decide if the medicine is safe. A person does."

### 0:45 to 1:05. The one human decision. (Tab 1)

Click **Record human disposition**. Type your name, pick **Replace**, type one sentence, submit.

"I am the pharmacist today. That is the only decision a person makes."

Watch the steps tick by themselves. Point at **Durable wakes**: *Poll sandbox courier, pending*. Point at **0 continue clicks**.

"That was the last human action. From here, nobody clicks."

Take your hands off the mouse for one visible second. Then:

"The next action is stored in Firestore. Cloud Scheduler wakes the agent every minute. When the courier confirms the handoff, the agent closes the case by itself.
Let me show you that on Google Cloud while it happens."

### 1:05 to 2:20. Proof on Google Cloud. (Tabs 2 to 5, about 18 seconds each)

- Tab 2, Cloud Run: "ColdClock itself is running here on Cloud Run. This revision takes all the traffic."
- Tab 3, Cloud Scheduler: "And this is what makes the workflow truly asynchronous: Cloud Scheduler wakes it every minute using a signed Google identity. Without that identity the agent answers 401."
- Tab 4, Firestore: refresh, open the newest `courier_status_poll` document. "Here is the pending action stored in Firestore. Nobody needs to keep the browser open." Refresh once more. "There. The background worker completed it."
- Tab 5, Logs: "And here is that scheduler call reaching the running service successfully, 200 every minute."

### 2:20 to 2:45. It finished by itself. (Tab 1)

Switch back. The page has already changed.

"No refresh. No click. The case is resolved.
The rail says: closed by a Cloud Scheduler wake, no operator. Background wakes: one fired.
The last line in the timeline is the background agent: courier confirmed handoff."

Click **Open signed autonomy proof**. Point at `closed_by_background_wake: true`, `operator_continue_clicks: 0`, and `signature`.

"This receipt is built from stored records and signed. Change one number and it fails."

### 2:45 to 3:05. One outage, every household. (Tab 1, press Simulate grid outage)

"A real outage is not one house. One message from the utility reaches every home we watch.
Each home gets its own watch. Warm fridge: sent to a pharmacist. Fine fridge: keep watching. Silent sensor: stop safely and ask a person."

### 3:05 to 3:20. When things break. (Tab 1, open /api/hardening/proof)

"Missing readings. A pharmacist who never answers. A courier that never confirms. A label that tries to give orders. A model that invents a number.
Every one of them stops safely. Twenty checks, twenty passed, live."

### 3:20 to 3:35. Close. (Tab 1, top of page)

"ColdClock: Gemini, Gemma, and an ADK agent for the evidence. Firestore for memory. Cloud Scheduler and Pub/Sub so it works while nobody is watching. A pharmacist for the one decision that must stay human. And a signed receipt for everything else.
The idea is simple: an alarm should not just tell you something went wrong. The agent should safely coordinate what happens next.
Everything here is synthetic, the demo clock is simulated and says so, and we claim no clinical result.
Code, diagram, and proofs are linked below. Thank you."

Stop recording.

## After recording

- Publish public on YouTube or Vimeo (not unlisted), English audio, captions on.
- Description: hosted URL, repo URL, and this sentence: "I created this piece of content for the purposes of entering the All Things Agentic Hackathon."
- Paste the link into the Devpost form and `submission-manifest.json` (`video_url`).

## If something goes wrong

- Run unattended is slow: keep talking; it lands within 30 seconds.
- Case not closed when you return: say "the scheduler ticks once a minute", show Firestore again, do the outage beat, come back. Never click Confirm household receipt.
- A 503 "live model evidence unavailable": say "it fails closed instead of faking a result", press Run unattended again.

## Why this matches the judging rules

- Problem and value in the first 20 seconds.
- Live, unedited execution with visible state changes: the UI, a Firestore document, and logs.
- Proof it runs on Google Cloud, shown in the middle where the app is waiting anyway.
- Architecture explained by pointing at real services, not slides.
- Honesty on camera: synthetic data, simulated clock, human decision.
