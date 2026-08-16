(() => {
  const configs = {
    "cold-clock": {
      name: "ColdClock",
      workflow: "#console",
      action: "#next-action",
      reset: "#reset-demo",
      proof: "/judges",
      steps: [
        ["monitoring", "Start with the observed package", "Trigger the synthetic outage.", "A real workflow must begin with an event, not an AI conclusion."],
        ["excursion_detected", "Build the reviewer packet", "Assemble the observed temperatures, duration and label evidence.", "A qualified reviewer needs facts without an invented clinical verdict."],
        ["awaiting_professional_review", "Record human disposition", "Use the named synthetic pharmacist decision.", "Clinical authority stays with a person; the agent cannot cross this gate."],
        ["replacement_approved", "Reserve the approved replacement", "Continue only after the human disposition exists.", "Inventory action before approval would be an unsafe automation shortcut."],
        ["fulfillment_prepared", "Dispatch accessible delivery", "Book the synthetic accessible courier slot.", "A recommendation has no impact until the approved action can reach the household."],
        ["delivery_dispatched", "Confirm receipt", "Record synthetic household receipt proof.", "Delivery dispatch is not resolution; the last handoff must be verified."],
        ["resolved", "Inspect the completed proof", "The case is closed with a source-bearing audit trail.", "Judges can now inspect the executable proof and architecture."],
      ],
    },
    "one-advisory": {
      name: "One Advisory",
      workflow: ".command",
      action: "#advance",
      reset: "#reset",
      proof: "/judges",
      steps: [
        ["authorized_advisory_received", "Activate the response fleet", "Match the authorized zone to critical facilities.", "The system begins after human issuance; it never invents an advisory."],
        ["proposals_ready", "Approve facility-specific work", "Review and deliver source-bearing proposals.", "Different facilities need different actions, but consequential outreach requires approval."],
        ["instructions_delivered", "Collect facility evidence", "Receive acknowledgements, constraints and one failed contact.", "Message delivery is not the same as verified institutional response."],
        ["responses_in_progress", "Surface the resource conflict", "Detect competing requests without selecting a winner.", "Scarce-resource allocation must remain with accountable human authority."],
        ["resource_conflict", "Make the human allocation", "Choose the bounded option as the synthetic incident commander.", "The fleet provides evidence and options—not an autonomous allocation."],
        ["allocation_approved", "Escalate the missing response", "Route the missed acknowledgement to the duty officer.", "Silence must become visible recovery work, never a fake acknowledgement."],
        ["response_verified", "Apply authorized rescission", "Run differentiated recovery checks after human rescission.", "Recovery needs the same facility-specific discipline as activation."],
        ["closed", "Inspect the managed proof", "The response and recovery trail is complete.", "Judges can now inspect executable proofs and the live managed platform."],
      ],
    },
    "plan-kept": {
      name: "Plan Kept",
      workflow: ".workspace",
      action: "#advance",
      reset: "#reset",
      proof: "/judges",
      steps: [
        ["plan_loaded", "Open separate perspectives", "Create one bounded session for each fictional participant.", "Different voices remain separate so one account cannot silently overwrite another."],
        ["perspectives_open", "Collect participant-controlled input", "Demonstrate private, facilitator and team sharing choices.", "Consent is part of the data model—not a one-time checkbox."],
        ["perspectives_collected", "Synthesize only shared evidence", "Classify agreement, conflict and unknowns.", "Private or skipped responses must remain outside the synthesis."],
        ["clarification_ready", "Answer a targeted question", "Add operational evidence for the disagreement.", "The system asks what could resolve uncertainty instead of scoring credibility."],
        ["facilitator_review", "Record the human finding", "Approve a bounded repair as the synthetic facilitator.", "AI cannot decide that a plan failed or modify the support plan."],
        ["repair_approved", "Return after the repair", "Advance the fictional clock to the follow-up.", "Assigned tasks are not proof that support became usable in practice."],
        ["followup_due", "Ask about lived availability", "Let the fictional student confirm what happened this time.", "The person receiving support—not an operational checkbox—closes the loop."],
        ["closed", "Inspect the collaboration proof", "The promise-to-practice loop is complete.", "Judges can now inspect consent, revision and adversarial safeguards."],
      ],
    },
  };

  const config = configs[document.body.dataset.guide];
  if (!config) return;

  const workflow = document.querySelector(config.workflow);
  const startButton = document.querySelector("#start-guide");
  if (!workflow || !startButton) return;

  const root = document.createElement("div");
  root.className = "guided-shell";
  root.innerHTML = `
    <button class="guided-launcher" type="button" aria-label="Open guided demo">
      <span aria-hidden="true">?</span><b>Guide me</b>
    </button>
    <aside class="guided-panel" aria-label="Guided demo" hidden>
      <header class="guided-header">
        <div><span class="guided-kicker">GUIDED DEMO</span><b class="guided-mini-title">Next best action</b></div>
        <div class="guided-header-actions">
          <a href="${config.proof}" aria-label="Open judge view">Judge view</a>
          <button type="button" data-guide-action="expand" aria-label="Expand guide">Open</button>
          <button type="button" data-guide-action="exit" aria-label="Exit guided demo">×</button>
        </div>
      </header>
      <div class="guided-content">
        <div class="guided-progress-copy"><span data-guide-progress></span><span data-guide-percent></span></div>
        <div class="guided-progress" aria-hidden="true"><i></i></div>
        <h2 data-guide-title></h2>
        <p class="guided-instruction" data-guide-instruction></p>
        <div class="guided-why"><span>WHY THIS MATTERS</span><p data-guide-why></p></div>
        <details class="guided-roadmap"><summary>View the full path</summary><ol></ol></details>
        <p class="guided-status" role="status" aria-live="polite"></p>
      </div>
      <footer class="guided-footer">
        <button class="guided-secondary" type="button" data-guide-action="back">Back</button>
        <button class="guided-secondary" type="button" data-guide-action="restart">Restart</button>
        <button class="guided-primary" type="button" data-guide-action="show">Show next click <span>→</span></button>
        <a class="guided-primary guided-proof" href="${config.proof}">Open judge proof <span>→</span></a>
      </footer>
    </aside>`;
  document.body.appendChild(root);

  const launcher = root.querySelector(".guided-launcher");
  const panel = root.querySelector(".guided-panel");
  const progressBar = root.querySelector(".guided-progress i");
  const roadmap = root.querySelector(".guided-roadmap ol");
  const status = root.querySelector(".guided-status");
  const showButton = root.querySelector('[data-guide-action="show"]');
  const backButton = root.querySelector('[data-guide-action="back"]');
  const proofButton = root.querySelector(".guided-proof");
  let active = false;
  let reviewIndex = null;
  let highlighted = null;

  const actualIndex = () => {
    const state = workflow.dataset.workflowState;
    const index = config.steps.findIndex((step) => step[0] === state);
    return Math.max(0, index);
  };

  function clearHighlight() {
    if (highlighted) highlighted.classList.remove("guided-target");
    highlighted = null;
  }

  function render() {
    const current = actualIndex();
    const shown = reviewIndex ?? current;
    const step = config.steps[shown];
    const complete = current === config.steps.length - 1 && reviewIndex === null;
    const reviewing = reviewIndex !== null;
    const percent = Math.round(((current + 1) / config.steps.length) * 100);
    root.querySelector("[data-guide-progress]").textContent = `Step ${shown + 1} of ${config.steps.length}${reviewing ? " · review" : ""}`;
    root.querySelector("[data-guide-percent]").textContent = `${percent}% complete`;
    progressBar.style.width = `${percent}%`;
    root.querySelector("[data-guide-title]").textContent = step[1];
    root.querySelector("[data-guide-instruction]").textContent = step[2];
    root.querySelector("[data-guide-why]").textContent = step[3];
    root.querySelector(".guided-mini-title").textContent = step[1];
    status.textContent = reviewing ? "Reviewing a completed step. The live workflow has not moved backward." : "";
    backButton.disabled = shown === 0;
    backButton.textContent = reviewing ? "Previous" : "Back";
    showButton.textContent = reviewing ? "Return to current step" : "Show next click →";
    showButton.hidden = complete;
    proofButton.hidden = !complete;
    roadmap.innerHTML = config.steps.map((item, index) => {
      const state = index < current ? "done" : index === current ? "current" : "locked";
      return `<li class="${state}"><button type="button" data-guide-step="${index}" ${index > current ? "disabled" : ""}><span>${index < current ? "✓" : index + 1}</span><b>${item[1]}</b><small>${state === "current" ? "Current" : state === "done" ? "Complete" : "Locked"}</small></button></li>`;
    }).join("");
  }

  function openGuide(scroll = true) {
    active = true;
    reviewIndex = null;
    panel.hidden = false;
    panel.classList.remove("is-minimized");
    launcher.hidden = true;
    render();
    if (scroll) workflow.scrollIntoView({ behavior: "smooth", block: "start" });
    window.localStorage.setItem(`${document.body.dataset.guide}-guide-used`, "true");
  }

  function exitGuide() {
    active = false;
    reviewIndex = null;
    clearHighlight();
    panel.hidden = true;
    launcher.hidden = false;
    startButton.focus({ preventScroll: true });
  }

  function showTarget() {
    if (reviewIndex !== null) {
      reviewIndex = null;
      render();
      return;
    }
    const target = document.querySelector(config.action);
    clearHighlight();
    if (!target) {
      status.textContent = "The next control is unavailable. Restart the fictional workflow and try again.";
      return;
    }
    if (target.disabled) {
      status.textContent = "The current action is still finishing. The guide will update when it is ready.";
      return;
    }
    highlighted = target;
    target.classList.add("guided-target");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => target.focus({ preventScroll: true }), 350);
    panel.classList.add("is-minimized");
    status.textContent = `Now select “${target.textContent.trim()}”.`;
  }

  startButton.addEventListener("click", () => openGuide(true));
  launcher.addEventListener("click", () => openGuide(false));
  root.addEventListener("click", (event) => {
    const action = event.target.closest("[data-guide-action]")?.dataset.guideAction;
    const stepButton = event.target.closest("[data-guide-step]");
    if (stepButton) {
      const requested = Number(stepButton.dataset.guideStep);
      reviewIndex = requested === actualIndex() ? null : requested;
      panel.classList.remove("is-minimized");
      render();
      return;
    }
    if (action === "exit") exitGuide();
    if (action === "expand") panel.classList.remove("is-minimized");
    if (action === "show") showTarget();
    if (action === "back") {
      reviewIndex = Math.max(0, (reviewIndex ?? actualIndex()) - 1);
      panel.classList.remove("is-minimized");
      render();
    }
    if (action === "restart") {
      document.querySelector(config.reset)?.click();
      reviewIndex = null;
      panel.classList.remove("is-minimized");
      status.textContent = "Restarting the fictional workflow…";
      window.setTimeout(() => active && render(), 650);
    }
  });

  new MutationObserver(() => {
    if (!active) return;
    clearHighlight();
    reviewIndex = null;
    panel.classList.remove("is-minimized");
    render();
  }).observe(workflow, { attributes: true, attributeFilter: ["data-workflow-state", "aria-busy"] });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && active) exitGuide();
  });

  launcher.hidden = false;
  if (new URLSearchParams(window.location.search).get("guide") === "1") {
    window.setTimeout(() => openGuide(true), 450);
  }
})();
