# ColdClock demo runbook (one take, about 3:40)

Every step has three lines: DO (mouse), POINT (cursor), SAY (words). Read SAY exactly; it is written to be spoken.
Only the first four minutes are judged. No cuts. If something misfires, say what you see and keep going.

## Part A. Ten minutes before recording

1. Run in a terminal: `python scripts/browser_check.py --url https://cold-clock-109051079423.us-central1.run.app --wait 240`
   Wait for `8/8 browser checks passed`. This proves today's path is green and warms the service.
2. Open exactly these five tabs, in this order, logged into Google Cloud, each fully loaded:
   - Tab 1: https://cold-clock-109051079423.us-central1.run.app
     Scroll down until the white card titled LIVE CASE fills the screen. "Show everything" must be unticked. Light theme.
     The headline must read "The fridge is being watched." with a green "Run unattended" button. If it shows another case, use the Case dropdown and pick any entry that says "Monitoring normally", or click the green button once and reload.
   - Tab 2: https://console.cloud.google.com/run/detail/us-central1/cold-clock/revisions?project=agentic-fleet-2026
   - Tab 3: https://console.cloud.google.com/cloudscheduler/jobs/us-central1/cold-clock-wake-scan?project=agentic-fleet-2026
   - Tab 4: https://console.cloud.google.com/firestore/databases/-default-/data/panel/cold_clock_wakes?project=agentic-fleet-2026
   - Tab 5: https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%20resource.labels.service_name%3D%22cold-clock%22%20httpRequest.requestUrl%3A%22%2Finternal%2Fwakes%2Fscan%22?project=agentic-fleet-2026
3. Close every other tab and window. No other websites, logos, or notifications on screen.
4. Browser zoom 100 percent, window wide. Start screen recording with microphone. Go to Tab 1.

## Part B. The take

### Step 1. The problem. 0:00 to 0:20. Tab 1.

DO: nothing. Stay on the LIVE CASE card.
POINT: the headline "The fridge is being watched."
SAY: "When the power goes out, a fridge with insulin in it sends an alarm. And then nothing happens. Someone still has to work out which medicine it was, how long it was warm, call a pharmacist, get a replacement, and make sure it arrives. Today, the alarm is only the beginning. ColdClock does that work by itself. It stops for one thing: the decision that belongs to a pharmacist."

### Step 2. One click. 0:20 to 0:50. Tab 1.

DO: click the green button "Run unattended". It takes 15 to 30 seconds. Keep talking while it works.
SAY (while it runs): "One click. ColdClock reads the medicine package, checks the storage evidence, and builds everything a pharmacist needs. Gemini reads the package. Gemma screens the label for hidden instructions. And a Google ADK agent builds the review packet from read-only evidence. Every value is checked against its source."
DO (when it stops): the headline changes to "Waiting for the pharmacist." Stops 1 and 2 show green ticks; stop 3 is open.
POINT: stop 1's grey text "145 min out of range, peak 95.2°F".
SAY: "The fridge was warm for 145 minutes."
POINT: stop 2's grey text "5 package fields, every one an exact quote".
SAY: "Five facts from the package, each one an exact quote from the image."
POINT: inside stop 3, the green box "AI DISPOSITION: NONE. HUMAN DECISION REQUIRED".
SAY: "And here it stops on purpose. The system will not decide if the medicine is safe. A person does."
POINT: the green line under the packet "ADK agent built this packet, verified".
SAY: "The agent wrote this packet, and every number was verified against the tools it used."

### Step 3. The one human decision. 0:50 to 1:15. Tab 1.

DO: click the green button, now labelled "Record the pharmacist's decision". A dialog opens.
DO: in "Reviewer name and credential" type: Avery Chen, PharmD
DO: leave Disposition as "Replace".
DO: in "Independent rationale" type: Out of range for 145 minutes, replacement is appropriate.
DO: click "Record human decision".
SAY (while typing): "I am the pharmacist today. This is the only decision a person makes."
DO: watch. Stop 3 ticks green. Stop 4 opens by itself with the title "Nobody clicks from here." The green button turns into a grey "Hands off".
POINT: the line under the headline: "0 continue clicks".
SAY: "That was the last human action. From here, nobody clicks."
DO: take your hand off the mouse and keep it off for one full second.
POINT: inside stop 4, the row "Poll sandbox courier at ETA, pending".
SAY: "The next action is stored in Firestore. Cloud Scheduler wakes the agent every minute. When the courier confirms the handoff, the agent closes the case by itself."
POINT: the last line in stop 4: "Cloud Scheduler scanned N seconds ago (verified Google OIDC)".
SAY: "You can see the scheduler calling it right now. Let me show you that on Google Cloud while it happens."

### Step 4. Proof on Google Cloud. 1:15 to 2:25. Tabs 2, 3, 4, 5.

DO: switch to Tab 2 (Cloud Run, revisions).
POINT: the service name "cold-clock" at the top, then the top revision row with "100%" traffic.
SAY: "ColdClock itself is running here on Cloud Run. One container. This revision takes all the traffic."

DO: switch to Tab 3 (Cloud Scheduler job).
POINT: the frequency "* * * * *" (every minute), then the "Last run" time, then the auth section showing the OIDC service account.
SAY: "And this is what makes the workflow truly asynchronous. Cloud Scheduler wakes it every minute using a signed Google identity. Without that identity, the agent answers 401."

DO: switch to Tab 4 (Firestore, collection cold_clock_wakes). Click the refresh icon at the top of the panel. Click the newest document (the list is sorted by id; if unsure, click any and check the fields).
POINT: the field "kind: courier_status_poll", then "status: pending", then "run_id" (that is the case id).
SAY: "Here is the pending action stored in Firestore. Nobody needs to keep the browser open."
DO: wait about 20 seconds, click refresh again, click the same document.
POINT: "status: done".
SAY: "There. The background worker completed it."
(If it still says pending, say "the scheduler ticks once a minute", move to Tab 5, and come back to this document after Tab 5.)

DO: switch to Tab 5 (Logs).
POINT: the most recent line with "/internal/wakes/scan" and status 200.
SAY: "And here is that scheduler call reaching the running service successfully, 200, every minute."

### Step 5. It finished by itself. 2:25 to 2:50. Tab 1.

DO: switch back to Tab 1. Do not refresh. Do not click.
POINT: the headline, now "Delivered. Closed by a Cloud Scheduler wake, no operator."
SAY: "No refresh. No click. Delivered. Closed by a Cloud Scheduler wake, no operator."
POINT: the line under the headline: "0 continue clicks, 1 human decision, 1 background wake fired".
SAY: "Zero clicks after the decision. One human decision. One background wake."
POINT: stop 5's four boxes, left to right.
SAY: "Clicks after the decision, zero. Background wakes fired, one. Human decisions, one. Receipt, signed and verified."
DO: click the link "Open signed autonomy proof" under the four boxes. A JSON page opens in a new tab.
POINT: `closed_by_background_wake: true`, then `operator_continue_clicks: 0`, then `signature`.
SAY: "This receipt is built from stored records and signed. Change one number and it fails."
DO: close that tab, back to Tab 1.

### Step 6. One outage, every household. 2:50 to 3:10. Tab 1.

DO: click the white button "Simulate grid outage" (top right of the card). The card switches to one of three new households.
POINT: the headline, then the Case dropdown, then stop 1's grey text.
SAY: "A real outage is not one house. One message from the utility reaches every home we watch. Each home gets its own background watch. Warm fridge: sent to a pharmacist. Fine fridge: keep watching. Silent sensor: stop safely and ask a person."

### Step 7. When things break. 3:10 to 3:25. Tab 1.

DO: in the address bar of a new tab, open https://cold-clock-109051079423.us-central1.run.app/api/hardening/proof
POINT: `"passed": 20, "total": 20` at the top, then scroll slowly through the check names.
SAY: "Missing readings. A pharmacist who never answers. A courier that never confirms. A label that tries to give orders. A model that invents a number. Every one of them stops safely. Twenty checks, twenty passed, live."
DO: close the tab, back to Tab 1.

### Step 8. Close. 3:25 to 3:40. Tab 1.

DO: scroll up so the ColdClock header and the LIVE CASE card are both visible.
SAY: "ColdClock: Gemini, Gemma, and an ADK agent for the evidence. Firestore for memory. Cloud Scheduler and Pub/Sub so it works while nobody is watching. A pharmacist for the one decision that must stay human. And a signed receipt for everything else. The idea is simple: an alarm should not just tell you something went wrong. The agent should safely coordinate what happens next. Everything here is synthetic, the demo clock is simulated and says so, and we claim no clinical result. Code, diagram, and proofs are linked below. Thank you."
DO: stop recording.

## Part C. After recording

1. Upload to YouTube as Public (not Unlisted). Title: "ColdClock: All Things Agentic Hackathon". Turn on auto captions.
2. Description, paste exactly:
   ColdClock, an autonomous medication-excursion agent on Google Cloud. Live: https://cold-clock-109051079423.us-central1.run.app  Code: https://github.com/usv240/cold-clock  I created this piece of content for the purposes of entering the All Things Agentic Hackathon.
3. Paste the video link into the Devpost form, and into `submission-manifest.json` under `video_url`.

## Part D. If something goes wrong

- "Run unattended" takes more than 30 seconds: keep talking through Step 2's SAY; it will land.
- The case has not closed when you return in Step 5: say "the scheduler ticks once a minute", show Tab 4 again, do Step 6, then come back; it will be closed. Never click anything else on the card.
- A red message "live model evidence unavailable": say "it fails closed instead of faking a result", click the green button again.
- The Firestore panel is empty: type `cold_clock_wakes` in the collection search box at the top left of the Firestore data panel.
