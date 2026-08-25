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
  monitoring: { label: "Inject synthetic outage event", note: "One event automatically routes the evidence packet to review.", endpoint: "outage" },
  excursion_detected: { label: "Resume safe automation", note: "Routes observed facts without a clinical conclusion.", endpoint: "autopilot" },
  awaiting_professional_review: { label: "Record human disposition", note: "A qualified reviewer must enter their own decision and rationale.", endpoint: "review" },
  replacement_approved: { label: "Resume safe automation", note: "The approved path reserves and dispatches without more operator steps.", endpoint: "autopilot" },
  fulfillment_prepared: { label: "Resume safe automation", note: "Books the accessible synthetic courier slot.", endpoint: "autopilot" },
  delivery_dispatched: { label: "Confirm household receipt", note: "Optional. If nobody clicks, the Cloud Scheduler wake polls the sandbox courier at the ETA and closes the case by itself.", endpoint: "confirm-delivery" },
  resolved: { label: "Case resolved", note: "Reset the case to run the story again.", endpoint: null },
};

let currentCase = null;
let autoRunning = false;
let caseSummaries = [];
let pollTimer = null;
const POLL_INTERVAL_MS = 5000;
const WAITING_STATES = new Set(["monitoring", "awaiting_professional_review", "delivery_dispatched", "excursion_detected", "replacement_approved", "fulfillment_prepared"]);

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

async function refreshCases(preferredId = currentCase?.case_id) {
  const data = await api("/api/pilot/cases");
  caseSummaries = data.cases;
  const select = $("#case-select");
  select.innerHTML = caseSummaries.length
    ? caseSummaries.map((row) => `<option value="${escapeHtml(row.case_id)}">${escapeHtml(row.case_reference)} · ${escapeHtml(row.medication)} · ${escapeHtml(statusCopy(row.status))}</option>`).join("")
    : '<option value="">No cases yet</option>';
  if (preferredId && caseSummaries.some((row) => row.case_id === preferredId)) select.value = preferredId;
}

async function loadCase(caseId) {
  if (!caseId) return;
  $("#console").setAttribute("aria-busy", "true");
  try { render(await api(`/api/cases/${caseId}`)); }
  catch (error) { toast(error.message); }
  finally { $("#console").setAttribute("aria-busy", "false"); }
}

function wakeCopy(kind) {
  return {
    courier_status_poll: "Poll sandbox courier at ETA",
    review_followup: "Review reminder",
    receipt_followup: "Receipt reminder",
    outage_watch: "Outage watch: judge from readings",
  }[kind] || kind.replaceAll("_", " ");
}

async function simulateOutage() {
  const button = $("#outage-fanout");
  button.disabled = true;
  $("#console").setAttribute("aria-busy", "true");
  try {
    const result = await api("/api/demo/outage-fanout", { method: "POST", body: JSON.stringify({ service_area: "grid-7", enroll: 3 }) });
    await refreshCases(result.affected_cases[0]);
    await loadCase(result.affected_cases[0]);
    toast(`Grid outage ${result.outage_id}: ${result.affected_cases.length} enrolled cases armed with outage watches. Each will be judged from its own readings by the background worker.`);
  } catch (error) { toast(error.message); }
  finally { button.disabled = false; $("#console").setAttribute("aria-busy", "false"); }
}

async function renderWakes(caseId) {
  const list = $("#wake-list");
  if (!list || !caseId) return;
  try {
    const data = await api(`/api/cases/${encodeURIComponent(caseId)}/wakes`);
    if (!data.wakes.length) {
      list.innerHTML = '<li class="wake-empty">No durable wakes yet. Dispatching a delivery registers one.</li>';
      return;
    }
    list.innerHTML = data.wakes.map((row) => `
      <li class="wake-row" data-status="${escapeHtml(row.status)}">
        <span class="wake-state" aria-hidden="true"></span>
        <div><b>${escapeHtml(wakeCopy(row.kind))}</b><small>${escapeHtml(row.status)} · due ${new Date(row.due_at).toLocaleTimeString([], {hour: "numeric", minute: "2-digit"})}${row.cancelled_reason ? ` · ${escapeHtml(row.cancelled_reason)}` : ""}</small></div>
      </li>`).join("");
    $("#simulated-now").textContent = `Simulated now ${new Date(data.simulated_now).toLocaleTimeString([], {hour: "numeric", minute: "2-digit"})}`;
  } catch (error) {
    list.innerHTML = `<li class="wake-empty">${escapeHtml(error.message)}</li>`;
  }
  renderWorkerStatus();
}

async function renderWorkerStatus() {
  const node = $("#worker-status");
  if (!node) return;
  try {
    const status = await api("/api/background/status");
    if (status.last_scan_at == null) {
      node.textContent = "Cloud Scheduler: no scan recorded since this instance started.";
      node.dataset.state = "unknown";
      return;
    }
    const mode = status.last_identity?.mode === "google-oidc" ? "verified Google OIDC" : status.last_identity?.mode || "unknown";
    node.textContent = `Cloud Scheduler scanned ${status.seconds_since_last_scan}s ago (${mode}) · ${status.scans} scans · ${status.dispatched_total} wakes fired${status.pushes ? ` · ${status.pushes} Pub/Sub pushes` : ""}`;
    node.dataset.state = status.seconds_since_last_scan <= 120 ? "live" : "stale";
  } catch (error) {
    node.textContent = "Cloud Scheduler status unavailable.";
    node.dataset.state = "unknown";
  }
}

async function pollActiveCase() {
  if (document.hidden || !currentCase || autoRunning) return;
  try {
    const fresh = await api(`/api/cases/${encodeURIComponent(currentCase.case_id)}`);
    if (fresh.record_version === currentCase.record_version) return;
    const before = currentCase.autonomy?.background_wakes_fired || 0;
    render(fresh);
    await refreshCases(fresh.case_id);
    if ((fresh.autonomy?.background_wakes_fired || 0) > before) {
      toast(fresh.autonomy?.closed_by_background_wake ? "Cloud Scheduler wake closed the case. Nobody clicked." : "A background wake advanced the case.");
    }
  } catch (error) { /* transient poll failure; the next tick retries */ }
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = window.setInterval(pollActiveCase, POLL_INTERVAL_MS);
}

function openDialog(id) {
  const dialog = $(`#${id}`);
  if (dialog && !dialog.open) dialog.showModal();
}

function closeDialog(id) {
  const dialog = $(`#${id}`);
  if (dialog?.open) dialog.close();
}
function statusCopy(status) {
  return {
    monitoring: "Monitoring normally",
    evidence_incomplete: "Safe stop: evidence incomplete",
    review_escalated: "Review escalated to backup",
    stock_escalated: "Stock escalation",
    delivery_choice_required: "Delivery choice required",
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
    <div class="packet-row"><span>Verified package fields</span><b>${packet.package_fields_verified}/${caseData.extraction?.accuracy?.total ?? packet.package_fields_verified}</b></div>
    ${decision ? `<div class="human-stamp">HUMAN REVIEW · ${escapeHtml(decision.reviewer)}</div><p>${escapeHtml(decision.rationale)}</p>` : `<div class="human-stamp">AI DISPOSITION: NONE · HUMAN DECISION REQUIRED</div>`}`;
}

function renderJourney(status) {
  const currentIndex = stateOrder.indexOf(status);
  $$("#journey li").forEach((item, index) => {
    item.classList.toggle("complete", index < currentIndex || status === "resolved");
    item.classList.toggle("active", index === currentIndex && status !== "resolved");
  });
}

function renderAutonomy(data = {}, proof = {}) {
  const automatic = proof.automatic_trace_events || 0;
  const human = proof.human_authority_events || 0;
  const fired = data.background_wakes_fired || 0;
  const wait = String(data.current_wait || "none").replaceAll("_", " ");
  $("#autonomy-receipt").dataset.complete = String(Boolean(data.complete));
  $("#autonomy-title").textContent = data.closed_by_background_wake
    ? "Closed by a Cloud Scheduler wake — no operator"
    : data.complete ? "Bounded autonomous run complete" : automatic ? "Safe work is advancing automatically" : "Monitoring until the next real event";
  $("#autonomy-trigger").textContent = (proof.operator_continue_clicks || 0) + " continue clicks";
  $("#autonomy-actions").textContent = automatic + " traced agent event" + (automatic === 1 ? "" : "s");
  $("#autonomy-human").textContent = human + " protected decision" + (human === 1 ? "" : "s");
  $("#autonomy-background").textContent = fired + " fired" + (data.closed_by_background_wake ? " · closed case" : (data.pending_background_wakes || []).length ? ` · ${data.pending_background_wakes.length} pending` : "");
  $("#autonomy-wait").textContent = data.complete ? (data.closed_by_background_wake ? "Closed by courier confirmation" : "Closed with receipt proof") : wait;
}

function renderPacketAgent(receipt) {
  const node = $("#packet-agent");
  if (!node) return;
  if (!receipt) {
    node.className = "injection-screen";
    node.innerHTML = `<b>Review-packet agent</b><span>On the deployed service a Google ADK agent assembles this packet through three scoped read-only tools; a verifier checks every value against tool output before routing.</span>`;
    return;
  }
  if (!receipt.live) {
    node.className = "injection-screen";
    node.innerHTML = `<b>Deterministic packet</b><span>${escapeHtml(receipt.reason || receipt.mode)}</span>`;
    return;
  }
  node.className = `injection-screen ${receipt.accepted ? "clean" : "flagged"}`;
  node.innerHTML = receipt.accepted
    ? `<b>ADK agent packet accepted</b><span>${escapeHtml(receipt.model)} · ${(receipt.tool_calls || []).length} scoped tool calls · ${(receipt.verified_fields || []).length} values verified against tool output · ${receipt.latency_ms} ms</span>`
    : `<b>ADK agent packet rejected — deterministic packet used</b><span>${escapeHtml((receipt.rejected_fields || []).join(", ") || receipt.reason)} · the agent cannot invent or editorialise</span>`;
}

function renderInjectionScreen(screen) {
  const node = $("#injection-screen");
  if (!node) return;
  if (!screen) {
    node.className = "injection-screen";
    node.innerHTML = `<b>Injection screen</b><span>Runs with live models on the deployed service: pattern layer plus Gemma 4 quarantine instruction-shaped package text before routing.</span>`;
    return;
  }
  node.className = `injection-screen ${screen.clean ? "clean" : "flagged"}`;
  node.innerHTML = `<b>${screen.clean ? "Package text screened — clean" : `${screen.quarantined_spans} instruction-shaped span${screen.quarantined_spans === 1 ? "" : "s"} quarantined`}</b><span>${escapeHtml(screen.model)} · ${escapeHtml(screen.mode)}${screen.live ? "" : " · pattern layer only"} · ${screen.latency_ms} ms · never a medication decision</span>`;
}
function render(caseData) {
  currentCase = caseData;
  const status = caseData.status;
  renderAutonomy(caseData.autonomy, caseData.autonomy_proof);
  $("#status-title").textContent = statusCopy(status);
  $("#case-id").textContent = `${caseData.household.display_name} · ${caseData.case_id}`;
  $("#case-origin").textContent = caseData.origin === "pilot_input" ? `${caseData.data_class} pilot input` : "sample fixture";
  if ([...$("#case-select").options].some((option) => option.value === caseData.case_id)) $("#case-select").value = caseData.case_id;
  $("#record-sensor").disabled = caseData.status !== "monitoring";
  $("#progress-count").textContent = caseData.timeline.length;
  $("#status-orb").className = `status-orb ${status === "excursion_detected" ? "attention" : status === "awaiting_professional_review" ? "waiting" : ""}`;
  const readings = caseData.sensor.readings;
  const latest = readings[readings.length - 1];
  $("#latest-temperature").textContent = `${latest.fahrenheit.toFixed(1)}°F`;
  $("#observed-duration").textContent = caseData.excursion ? `${caseData.excursion.observed_minutes} min` : "No excursion";
  $("#power-state").textContent = latest.power === "on" ? "On" : "Outage";
  renderChart(readings);
  renderTimeline(caseData.timeline);
  $("#public-trace-link").href = `/api/cases/${encodeURIComponent(caseData.case_id)}/trace`;
  $("#autonomy-proof-link").href = `/api/cases/${encodeURIComponent(caseData.case_id)}/autonomy-proof`;
  renderJourney(status);
  renderReview(caseData);
  $("#verified-fields").innerHTML = caseData.extraction.fields.map((field) => `<div class="verified-field"><span>${escapeHtml(field.key)}</span><b>${escapeHtml(field.value)}</b><small>Exact quote verified</small></div>`).join("");
  $("#package-provenance").textContent = caseData.origin === "pilot_input" ? "USER-CONFIRMED VERBATIM" : "SYNTHETIC DEMONSTRATION";
  $("#package-name").textContent = caseData.medication.display_name;
  $("#package-strength").textContent = caseData.medication.strength;
  $("#package-form").textContent = caseData.medication.form;
  $("#package-lot").textContent = `Lot ${caseData.medication.lot}`;
  $("#label-source").href = caseData.label_evidence.url;
  renderInjectionScreen(caseData.injection_screen);
  renderPacketAgent(caseData.packet_agent);
  const action = actionMap[status];
  const button = $("#next-action");
  button.textContent = action?.label || "Workflow complete";
  button.disabled = !action?.endpoint || autoRunning;
  $("#control-note").textContent = action?.note || "Reset to replay the synthetic case.";
  $("#advance-clock").disabled = !WAITING_STATES.has(status);
  renderWakes(caseData.case_id);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);
}

async function resetCase() {
  $("#console").setAttribute("aria-busy", "true");
  try {
    const created = await api("/api/cases", { method: "POST" });
    render(created);
    await refreshCases(created.case_id);
    toast("Sample case added to the queue.");
  } catch (error) { toast(error.message); }
  finally { $("#console").setAttribute("aria-busy", "false"); }
}

async function advance(autoApproval = false) {
  if (!currentCase) return;
  const action = actionMap[currentCase.status];
  if (!action?.endpoint) return;
  if (action.endpoint === "review" && !autoApproval) {
    openDialog("review-dialog");
    return;
  }
  $("#console").setAttribute("aria-busy", "true");
  $("#next-action").disabled = true;
  try {
    const options = { method: "POST" };
    if (action.endpoint === "review") {
      options.body = JSON.stringify({ disposition: "replace", reviewer_name: "Avery Chen, PharmD — synthetic", rationale: "Replacement approved for the automated synthetic demonstration only." });
    }
    const updated = await api(`/api/cases/${currentCase.case_id}/${action.endpoint}`, options);
    render(updated);
    await refreshCases(updated.case_id);
    toast(`${statusCopy(updated.status)}.`);
  } catch (error) { toast(error.message); }
  finally { $("#console").setAttribute("aria-busy", "false"); }
}

async function runAuto() {
  if (autoRunning) return;
  autoRunning = true;
  $("#auto-demo").disabled = true;
  $("#console").setAttribute("aria-busy", "true");
  try {
    const completed = await api("/api/demo/full", { method: "POST" });
    render(completed);
    await refreshCases(completed.case_id);
    toast("One trigger completed the outage-to-receipt workflow.");
  } catch (error) {
    toast(error.message);
  } finally {
    autoRunning = false;
    $("#auto-demo").disabled = false;
    $("#console").setAttribute("aria-busy", "false");
    if (currentCase) render(currentCase);
  }
}

async function runUnattended() {
  if (autoRunning) return;
  autoRunning = true;
  $("#unattended-demo").disabled = true;
  $("#console").setAttribute("aria-busy", "true");
  try {
    const started = await api("/api/demo/unattended", { method: "POST", body: JSON.stringify({ stop_at_review: true }) });
    render(started);
    await refreshCases(started.case_id);
    toast("Live models read the package and the agent routed the packet. Record the pharmacist decision — everything after that click is automatic, including the scheduler-fired closure.");
  } catch (error) {
    toast(error.message);
  } finally {
    autoRunning = false;
    $("#unattended-demo").disabled = false;
    $("#console").setAttribute("aria-busy", "false");
    if (currentCase) render(currentCase);
  }
}

async function advanceClock() {
  const button = $("#advance-clock");
  button.disabled = true;
  try {
    const result = await api("/api/hardening/advance", { method: "POST", body: JSON.stringify({ minutes: 35, dispatch: false }) });
    toast(`Simulated clock advanced to ${new Date(result.now).toLocaleTimeString([], {hour: "numeric", minute: "2-digit"})}. The next Cloud Scheduler scan fires whatever is due.`);
    if (currentCase) await renderWakes(currentCase.case_id);
  } catch (error) { toast(error.message); }
  finally { button.disabled = !currentCase || !WAITING_STATES.has(currentCase.status); }
}

function setupTabs() {
  $$("[role=tab]").forEach((tab) => tab.addEventListener("click", () => {
    $$("[role=tab]").forEach((other) => other.setAttribute("aria-selected", String(other === tab)));
    $$(".tab-panel").forEach((panel) => { panel.hidden = panel.id !== `tab-${tab.dataset.tab}`; });
  }));
}

async function submitIntake(event) {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.currentTarget));
  const payload = {
    data_use_acknowledgement: true,
    data_class: "synthetic",
    case_reference: values.case_reference,
    contact_preference: values.contact_preference,
    mobility_note: values.mobility_note,
    medication: { display_name: values.display_name, strength: values.strength, form: values.form, lot: values.lot, opened_on: values.opened_on },
    package_transcription: values.package_transcription,
    label_source_title: values.label_source_title,
    label_source_url: values.label_source_url,
    jurisdiction: values.jurisdiction,
    quoted_storage_text: values.quoted_storage_text,
    monitoring_range_f: { minimum: Number(values.range_min), maximum: Number(values.range_max) },
    baseline_fahrenheit: Number(values.baseline),
    sensor_source: values.sensor_source,
  };
  try {
    const created = await api("/api/pilot/cases", { method: "POST", body: JSON.stringify(payload) });
    closeDialog("intake-dialog");
    render(created);
    await refreshCases(created.case_id);
    toast("Pilot case enrolled from supplied evidence.");
  } catch (error) { toast(error.message); }
}

async function submitSensor(event) {
  event.preventDefault();
  if (!currentCase) return;
  const values = Object.fromEntries(new FormData(event.currentTarget));
  const utc = (value) => new Date(`${value}:00Z`).toISOString();
  const payload = { event_id: values.event_id, started_at: utc(values.started_at), ended_at: utc(values.ended_at), minimum_fahrenheit: Number(values.minimum), maximum_fahrenheit: Number(values.maximum), latest_fahrenheit: Number(values.latest), power: values.power };
  try {
    const updated = await api(`/api/pilot/cases/${currentCase.case_id}/sensor-events`, { method: "POST", body: JSON.stringify(payload) });
    closeDialog("sensor-dialog");
    render(updated);
    await refreshCases(updated.case_id);
    toast(updated.last_ingestion?.duplicate ? "Duplicate event ignored safely." : updated.last_ingestion?.excursion_detected ? "Excursion recorded; professional review required." : "In-range event recorded.");
  } catch (error) { toast(error.message); }
}

async function submitReview(event) {
  event.preventDefault();
  if (!currentCase) return;
  const values = Object.fromEntries(new FormData(event.currentTarget));
  try {
    const updated = await api(`/api/cases/${currentCase.case_id}/review`, { method: "POST", body: JSON.stringify(values) });
    closeDialog("review-dialog");
    render(updated);
    await refreshCases(updated.case_id);
    toast("Named human disposition recorded.");
  } catch (error) { toast(error.message); }
}

document.addEventListener("DOMContentLoaded", async () => {
  setTheme(localStorage.getItem("coldclock-theme") || "dark");
  $("#theme-toggle").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
  $("#next-action").addEventListener("click", () => advance(false));
  $("#reset-demo").addEventListener("click", resetCase);
  $("#auto-demo").addEventListener("click", runAuto);
  $("#unattended-demo").addEventListener("click", runUnattended);
  $("#outage-fanout").addEventListener("click", simulateOutage);
  $("#advance-clock").addEventListener("click", advanceClock);
  $("#new-case").addEventListener("click", () => openDialog("intake-dialog"));
  $("#record-sensor").addEventListener("click", () => openDialog("sensor-dialog"));
  $("#case-select").addEventListener("change", (event) => loadCase(event.target.value));
  $("#intake-form").addEventListener("submit", submitIntake);
  $("#sensor-form").addEventListener("submit", submitSensor);
  $("#review-form").addEventListener("submit", submitReview);
  $$("[data-close]").forEach((button) => button.addEventListener("click", () => closeDialog(button.dataset.close)));
  setupTabs();
  try {
    await refreshCases();
    if (caseSummaries.length) await loadCase(caseSummaries[0].case_id);
    else await resetCase();
  } catch (error) { toast(error.message); }
  startPolling();
});