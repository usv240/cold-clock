const stateOrder = [
  "monitoring",
  "excursion_detected",
  "awaiting_professional_review",
  "replacement_approved",
  "fulfillment_prepared",
  "delivery_dispatched",
  "resolved",
];

const actionMap = {
  monitoring: { label: "Trigger power outage", note: "Starts a synthetic utility and sensor event.", endpoint: "outage" },
  excursion_detected: { label: "Assemble reviewer packet", note: "Routes observed facts without a clinical conclusion.", endpoint: "request-review" },
  awaiting_professional_review: { label: "Approve replacement as reviewer", note: "This click represents a named synthetic human pharmacist.", endpoint: "review" },
  replacement_approved: { label: "Reserve approved replacement", note: "Sandbox inventory cannot be touched before approval.", endpoint: "fulfillment" },
  fulfillment_prepared: { label: "Dispatch accessible delivery", note: "Books a synthetic accessible courier slot.", endpoint: "dispatch" },
  delivery_dispatched: { label: "Confirm household receipt", note: "Closes the loop with synthetic receipt proof.", endpoint: "confirm-delivery" },
  resolved: { label: "Case resolved", note: "Reset the case to run the story again.", endpoint: null },
};

let currentCase = null;
let autoRunning = false;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("coldclock-theme", theme);
  const dark = theme === "dark";
  $("#theme-toggle").setAttribute("aria-pressed", String(dark));
  $("#theme-toggle").setAttribute("aria-label", `Switch to ${dark ? "light" : "dark"} theme`);
  $(".theme-label").textContent = dark ? "Dark" : "Light";
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  window.setTimeout(() => node.classList.remove("show"), 2800);
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || "Request failed");
  }
  return response.json();
}

function statusCopy(status) {
  return {
    monitoring: "Monitoring normally",
    excursion_detected: "Excursion needs review",
    awaiting_professional_review: "Waiting for pharmacist",
    replacement_approved: "Replacement approved",
    review_resolved: "Professional review complete",
    fulfillment_prepared: "Replacement reserved",
    delivery_dispatched: "Delivery in progress",
    resolved: "Resolution complete",
  }[status] || status.replaceAll("_", " ");
}

function renderChart(readings) {
  const svg = $("#temperature-chart");
  const width = 720, height = 260, left = 50, right = 20, top = 20, bottom = 36;
  const minT = 30, maxT = 105;
  const x = (index) => left + (index / Math.max(1, readings.length - 1)) * (width - left - right);
  const y = (value) => top + ((maxT - value) / (maxT - minT)) * (height - top - bottom);
  const path = readings.map((row, index) => `${index ? "L" : "M"}${x(index).toFixed(1)} ${y(row.fahrenheit).toFixed(1)}`).join(" ");
  const grid = [40, 60, 80, 100].map((value) => `<line x1="${left}" y1="${y(value)}" x2="${width - right}" y2="${y(value)}" stroke="var(--line)" stroke-width="1"/><text x="0" y="${y(value) + 4}" fill="var(--text-faint)" font-size="10" font-family="DM Mono">${value}°F</text>`).join("");
  const dots = readings.map((row, index) => `<circle cx="${x(index)}" cy="${y(row.fahrenheit)}" r="5" fill="var(--bg-elevated)" stroke="${row.fahrenheit > 86 ? "var(--danger)" : "var(--brand)"}" stroke-width="3"><title>${row.fahrenheit}°F at ${new Date(row.at).toLocaleTimeString([], {hour: "numeric", minute: "2-digit"})}</title></circle>`).join("");
  svg.innerHTML = `${grid}<path d="${path}" fill="none" stroke="var(--brand)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>${dots}<text x="${width - right}" y="${height - 6}" text-anchor="end" fill="var(--text-faint)" font-size="9" font-family="DM Mono">Observed synthetic readings</text>`;
}

function renderTimeline(rows) {
  $("#timeline").innerHTML = [...rows].reverse().map((row) => `
    <article class="timeline-item ${row.status}">
      <span class="timeline-dot" aria-hidden="true"></span>
      <div class="timeline-copy">
        <div class="timeline-meta"><b>${escapeHtml(row.actor)}</b><time>${new Date(row.at).toLocaleTimeString([], {hour: "numeric", minute: "2-digit"})}</time></div>
        <h4>${escapeHtml(row.action)}</h4>
        <p>${escapeHtml(row.detail)}</p>
        ${row.evidence_ids.length ? `<span class="timeline-evidence">${row.evidence_ids.length} evidence link${row.evidence_ids.length > 1 ? "s" : ""}</span>` : ""}
      </div>
    </article>`).join("");
}

function renderReview(caseData) {
  const review = caseData.review;
  if (review.status === "not_requested") {
    $("#review-card").className = "empty-review";
    $("#review-card").innerHTML = `<span class="review-lock" aria-hidden="true"></span><h3>No review requested yet</h3><p>Trigger the synthetic outage and assemble the evidence packet.</p>`;
    return;
  }
  const packet = review.packet;
  const decision = review.decision;
  $("#review-card").className = "review-packet";
  $("#review-card").innerHTML = `
    <p class="eyebrow">${decision ? "Reviewed disposition" : "Pending human review"}</p>
    <h3>${decision ? escapeHtml(decision.disposition.replaceAll("_", " ")) : "Evidence packet ready"}</h3>
    <div class="packet-row"><span>Medicine</span><b>${escapeHtml(packet.medicine)}</b></div>
    <div class="packet-row"><span>Observed duration</span><b>${packet.observed_minutes} minutes</b></div>
    <div class="packet-row"><span>Maximum observed</span><b>${packet.maximum_fahrenheit}°F</b></div>
    <div class="packet-row"><span>Verified package fields</span><b>${packet.package_fields_verified}/4</b></div>
    ${decision ? `<div class="human-stamp">HUMAN REVIEW · ${escapeHtml(decision.reviewer)}</div><p>${escapeHtml(decision.rationale)}</p>` : `<div class="human-stamp">AI DISPOSITION: NONE · HUMAN DECISION REQUIRED</div>`}`;
}

function renderJourney(status) {
  const currentIndex = stateOrder.indexOf(status);
  $$("#journey li").forEach((item, index) => {
    item.classList.toggle("complete", index < currentIndex || status === "resolved");
    item.classList.toggle("active", index === currentIndex && status !== "resolved");
  });
}

function render(caseData) {
  currentCase = caseData;
  const status = caseData.status;
  $("#console").dataset.workflowState = status;
  $("#status-title").textContent = statusCopy(status);
  $("#case-id").textContent = `${caseData.case_id} · synthetic case`;
  $("#progress-count").textContent = caseData.timeline.length;
  $("#status-orb").className = `status-orb ${status === "excursion_detected" ? "attention" : status === "awaiting_professional_review" ? "waiting" : ""}`;
  const readings = caseData.sensor.readings;
  const latest = readings[readings.length - 1];
  $("#latest-temperature").textContent = `${latest.fahrenheit.toFixed(1)}°F`;
  $("#observed-duration").textContent = caseData.excursion ? `${caseData.excursion.observed_minutes} min` : "No excursion";
  $("#power-state").textContent = latest.power === "on" ? "On" : "Outage";
  renderChart(readings);
  renderTimeline(caseData.timeline);
  renderJourney(status);
  renderReview(caseData);
  $("#verified-fields").innerHTML = caseData.extraction.fields.map((field) => `<div class="verified-field"><span>${escapeHtml(field.key)}</span><b>${escapeHtml(field.value)}</b><small>Exact quote verified</small></div>`).join("");
  $("#label-source").href = caseData.label_evidence.url;
  const action = actionMap[status];
  const button = $("#next-action");
  button.textContent = action?.label || "Workflow complete";
  button.disabled = !action?.endpoint || autoRunning;
  $("#control-note").textContent = action?.note || "Reset to replay the synthetic case.";
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);
}

async function resetCase() {
  $("#console").setAttribute("aria-busy", "true");
  try {
    await api("/api/reset", { method: "POST" });
    render(await api("/api/cases", { method: "POST" }));
    toast("Synthetic case reset.");
  } catch (error) { toast(error.message); }
  finally { $("#console").setAttribute("aria-busy", "false"); }
}

async function advance() {
  if (!currentCase) return;
  const action = actionMap[currentCase.status];
  if (!action?.endpoint) return;
  $("#console").setAttribute("aria-busy", "true");
  $("#next-action").disabled = true;
  try {
    const options = { method: "POST" };
    if (action.endpoint === "review") {
      options.body = JSON.stringify({
        disposition: "replace",
        reviewer_name: "Avery Chen, PharmD — synthetic",
        rationale: "The documented demonstration excursion requires replacement in this tabletop case.",
      });
    }
    const updated = await api(`/api/cases/${currentCase.case_id}/${action.endpoint}`, options);
    render(updated);
    toast(`${statusCopy(updated.status)}.`);
  } catch (error) { toast(error.message); }
  finally { $("#console").setAttribute("aria-busy", "false"); }
}

const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));
async function runAuto() {
  if (autoRunning) return;
  autoRunning = true;
  $("#auto-demo").disabled = true;
  await resetCase();
  while (currentCase?.status !== "resolved") {
    await sleep(650);
    await advance();
  }
  autoRunning = false;
  $("#auto-demo").disabled = false;
  render(currentCase);
  toast("Complete outage-to-receipt story finished.");
}

function setupTabs() {
  $$("[role=tab]").forEach((tab) => tab.addEventListener("click", () => {
    $$("[role=tab]").forEach((other) => other.setAttribute("aria-selected", String(other === tab)));
    $$(".tab-panel").forEach((panel) => { panel.hidden = panel.id !== `tab-${tab.dataset.tab}`; });
  }));
}

document.addEventListener("DOMContentLoaded", async () => {
  setTheme(localStorage.getItem("coldclock-theme") || "dark");
  $("#theme-toggle").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
  $("#next-action").addEventListener("click", advance);
  $("#reset-demo").addEventListener("click", resetCase);
  $("#auto-demo").addEventListener("click", runAuto);
  setupTabs();
  await resetCase();
});

