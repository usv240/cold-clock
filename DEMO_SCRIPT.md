# ColdClock demo runbook

One take, about 3:40. Each step: **DO** (mouse), **POINT** (cursor on the **bold** thing), **SAY** (read as written).

---

## Setup, 10 minutes before

**Run:** `python scripts/browser_check.py --url https://cold-clock-109051079423.us-central1.run.app --wait 240` and wait for `8/8`.

**Open five tabs, in this order:**

1. App: https://cold-clock-109051079423.us-central1.run.app
   Scroll to the white **LIVE CASE** card. It must say **"The fridge is being watched."** with a green **Run unattended** button. "Show everything" unticked.
2. Cloud Run: https://console.cloud.google.com/run/detail/us-central1/cold-clock/revisions?project=agentic-fleet-2026
3. Cloud Scheduler: https://console.cloud.google.com/cloudscheduler/jobs/us-central1/cold-clock-wake-scan?project=agentic-fleet-2026
4. Firestore: https://console.cloud.google.com/firestore/databases/-default-/data/panel/cold_clock_wakes?project=agentic-fleet-2026
5. Logs: https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%20resource.labels.service_name%3D%22cold-clock%22%20httpRequest.requestUrl%3A%22%2Finternal%2Fwakes%2Fscan%22?project=agentic-fleet-2026

Close everything else. Zoom 100 percent. Start recording on Tab 1.

---

## Step 1. The problem · 0:00 · Tab 1

**DO:** nothing.

**POINT:** the headline **The fridge is being watched.**

**SAY:** "When the power goes out, a fridge with insulin in it sends an alarm. And then nothing happens. Someone still has to work out which medicine it was, how long it was warm, call a pharmacist, get a replacement, and make sure it arrives. Today, the alarm is only the beginning. ColdClock does that work by itself. It stops for one thing: the decision that belongs to a pharmacist."

---

## Step 2. One click · 0:20 · Tab 1

**DO:** click the green **Run unattended** button. It takes about 20 seconds. Talk while it works.

**SAY:** "One click. ColdClock reads the medicine package, checks the storage evidence, and builds everything a pharmacist needs. Gemini reads the package. Gemma screens the label for hidden instructions. And a Google ADK agent builds the review packet from read-only evidence. Every value is checked against its source."

When the headline changes to **Waiting for the pharmacist.**:

**POINT:** stop 1's grey text **145 min out of range, peak 95.2°F**
**SAY:** "The fridge was warm for 145 minutes."

**POINT:** stop 2's grey text **5 package fields, every one an exact quote**
**SAY:** "Five facts from the package, each one an exact quote from the image."

**POINT:** the green box **AI DISPOSITION: NONE**
**SAY:** "And here it stops on purpose. The system will not decide if the medicine is safe. A person does."

**POINT:** the green line **ADK agent built this packet, verified**
**SAY:** "The agent wrote this packet, and every number was verified against the tools it used."

---

## Step 3. The one human decision · 0:50 · Tab 1

**DO:** click the green **Record the pharmacist's decision** button. In the dialog type name `Avery Chen, PharmD`, keep **Replace**, type rationale `Out of range for 145 minutes, replacement is appropriate.` Click **Record human decision**.

**SAY:** "I am the pharmacist today. This is the only decision a person makes."

Stop 3 ticks. Stop 4 opens by itself. The button turns grey: **Hands off**.

**POINT:** under the headline, **0 continue clicks**
**SAY:** "That was the last human action. From here, nobody clicks."

**DO:** take your hand off the mouse for one full second.

**POINT:** inside stop 4, the row **Poll sandbox courier at ETA, pending**
**SAY:** "The next action is stored in Firestore. Cloud Scheduler wakes the agent every minute. When the courier confirms the handoff, the agent closes the case by itself."

**POINT:** the last line in stop 4, **Cloud Scheduler scanned N seconds ago (verified Google OIDC)**
**SAY:** "You can see the scheduler calling it right now. Let me show you that on Google Cloud while it happens."

---

## Step 4. Proof on Google Cloud · 1:15 · Tabs 2 to 5

**DO:** Tab 2.
**POINT:** the top revision row with **100%**
**SAY:** "ColdClock itself is running here on Cloud Run. One container. This revision takes all the traffic."

**DO:** Tab 3.
**POINT:** the frequency **\* \* \* \* \***, then the **service account** under authentication
**SAY:** "And this is what makes the workflow truly asynchronous. Cloud Scheduler wakes it every minute using a signed Google identity. Without that identity, the agent answers 401."

**DO:** Tab 4. Click **refresh**. Open the newest document.
**POINT:** **kind: courier_status_poll**, then **status: pending**
**SAY:** "Here is the pending action stored in Firestore. Nobody needs to keep the browser open."

**DO:** wait 20 seconds, click **refresh**, open the same document.
**POINT:** **status: done**
**SAY:** "There. The background worker completed it."

**DO:** Tab 5.
**POINT:** the newest line with **/internal/wakes/scan** and **200**
**SAY:** "And here is that scheduler call reaching the running service successfully. 200, every minute."

---

## Step 5. It finished by itself · 2:25 · Tab 1

**DO:** go back to Tab 1. Do not refresh. Do not click.

**POINT:** the headline **Delivered. Closed by a Cloud Scheduler wake, no operator.**
**SAY:** "No refresh. No click. Delivered. Closed by a Cloud Scheduler wake, no operator."

**POINT:** stop 5's four boxes, left to right: **0**, **1**, **1**, **Signed, verified**
**SAY:** "Clicks after the decision, zero. Background wakes fired, one. Human decisions, one. Receipt, signed and verified."

**DO:** click **Open signed autonomy proof**.
**POINT:** **closed_by_background_wake: true**, then **operator_continue_clicks: 0**, then **signature**
**SAY:** "This receipt is built from stored records and signed. Change one number and it fails."

**DO:** close that tab.

---

## Step 6. One outage, every household · 2:50 · Tab 1

**DO:** click the white **Simulate grid outage** button.

**POINT:** the new headline, then the **Case** dropdown.
**SAY:** "A real outage is not one house. One message from the utility reaches every home we watch. Each home gets its own background watch. Warm fridge: sent to a pharmacist. Fine fridge: keep watching. Silent sensor: stop safely and ask a person."

---

## Step 7. When things break · 3:10

**DO:** open a new tab: https://cold-clock-109051079423.us-central1.run.app/api/hardening/proof

**POINT:** **"passed": 20, "total": 20**
**SAY:** "Missing readings. A pharmacist who never answers. A courier that never confirms. A label that tries to give orders. A model that invents a number. Every one of them stops safely. Twenty checks, twenty passed, live."

**DO:** close the tab.

---

## Step 8. Close · 3:25 · Tab 1

**DO:** scroll up so the ColdClock header and the card are both visible.

**SAY:** "ColdClock: Gemini, Gemma, and an ADK agent for the evidence. Firestore for memory. Cloud Scheduler and Pub/Sub so it works while nobody is watching. A pharmacist for the one decision that must stay human. And a signed receipt for everything else. The idea is simple: an alarm should not just tell you something went wrong. The agent should safely coordinate what happens next. Everything here is synthetic, the demo clock is simulated and says so, and we claim no clinical result. Code, diagram, and proofs are linked below. Thank you."

**DO:** stop recording.

---

## After recording

- YouTube, **Public** (not Unlisted), captions on. Title: `ColdClock: All Things Agentic Hackathon`
- Description, paste exactly:
  `ColdClock, an autonomous medication-excursion agent on Google Cloud. Live: https://cold-clock-109051079423.us-central1.run.app  Code: https://github.com/usv240/cold-clock  I created this piece of content for the purposes of entering the All Things Agentic Hackathon.`
- Paste the link into Devpost and into `submission-manifest.json` (`video_url`).

## If something goes wrong

- **Run unattended is slow:** keep talking; it lands within 30 seconds.
- **Case not closed when you return in Step 5:** say "the scheduler ticks once a minute", show Tab 4 again, do Step 6, come back. Never click anything else on the card.
- **Red message "live model evidence unavailable":** say "it fails closed instead of faking a result", click the green button again.
- **Firestore panel empty:** type `cold_clock_wakes` in the collection search box.
