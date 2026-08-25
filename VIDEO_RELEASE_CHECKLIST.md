# Video release gate — ColdClock

- Keep the final runtime at 3:50 or less; the Rules evaluate only the first four minutes.
- Publish publicly, not unlisted, on YouTube or Vimeo with English narration or subtitles.
- Show one continuous live action: **Run unattended**, then the case closing by itself from the Cloud Scheduler wake — hands visibly off the keyboard during the wait.
- Show a deliberate failure path and both proof suites (8/8 and 12/12); do not rely only on slides.
- Show the `.run.app` address bar, Cloud Run revision, the `cold-clock-wake-scan` Cloud Scheduler job, the Firestore wake document going `pending → done`, the live Gemini/Embedding/Gemma receipts and Cloud Trace.
- Run `python scripts/demo_flow.py --url <run.app> --wait-for-scheduler 180` the same day and keep the 17/17 output.
- State: “All people, package, lot and connectors are synthetic. A qualified professional remains the clinical authority.”
- Avoid third-party logos, advertising and any endorsement implication; source names may appear only as cited evidence.
- Put this exact sentence in the public description if using the video for the content bonus: “I created this piece of content for the purposes of entering the All Things Agentic Hackathon.”
- Include the public repository and hosted URL in the description.
- Do not modify the submitted video, repository or live project during judging unless the Rules permit it.
