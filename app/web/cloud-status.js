(() => {
  const root = document.querySelector("[data-cloud-status]");
  if (!root) return;

  const trigger = root.querySelector(".cloud-status-trigger");
  const panel = root.querySelector(".cloud-status-panel");
  const services = root.querySelector(".cloud-status-services");
  const summary = root.querySelector("[data-cloud-summary]");
  const badge = root.querySelector("[data-cloud-badge]");
  const platformEndpoint = root.dataset.platformEndpoint;
  let pinned = false;

  const escapeHtml = (value) =>
    String(value).replace(/[&<>'"]/g, (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]
    );

  const show = (open) => {
    root.classList.toggle("is-open", open);
    trigger.setAttribute("aria-expanded", String(open));
    panel.setAttribute("aria-hidden", String(!open));
  };

  root.addEventListener("mouseenter", () => show(true));
  root.addEventListener("mouseleave", () => {
    if (!pinned) show(false);
  });
  root.addEventListener("focusin", () => show(true));
  root.addEventListener("focusout", (event) => {
    if (!pinned && !root.contains(event.relatedTarget)) show(false);
  });
  trigger.addEventListener("click", () => {
    pinned = !pinned;
    show(pinned);
  });
  document.addEventListener("click", (event) => {
    if (!root.contains(event.target)) {
      pinned = false;
      show(false);
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      pinned = false;
      show(false);
      trigger.focus();
    }
  });

  const requestJson = (url) =>
    fetch(url, { headers: { Accept: "application/json" } }).then((response) => {
      if (!response.ok) throw new Error(`${url} unavailable`);
      return response.json();
    });

  const render = (health, platform) => {
    const deployed =
      health.ok &&
      health.google_cloud_project &&
      health.google_cloud_project !== "local";
    const managedVerified = !platformEndpoint || platform?.live === true;
    const live = deployed && managedVerified;

    trigger.dataset.state = live ? "live" : deployed ? "checking" : "local";
    summary.textContent = live
      ? platformEndpoint
        ? `Service + managed agent plane verified · ${health.google_cloud_project}`
        : `Healthy deployment · ${health.google_cloud_project}`
      : deployed
        ? "Core service live · managed proof unavailable"
        : "Local development preview";
    badge.textContent = live ? "Live" : deployed ? "Partial" : "Local";
    services.innerHTML =
      (health.google_services || [])
        .map(
          (service) =>
            `<li><b>${escapeHtml(service.name)}</b><span>${escapeHtml(service.role)}</span></li>`
        )
        .join("") ||
      "<li><b>Stack unavailable</b><span>No service inventory was returned.</span></li>";
  };

  const healthRequest = requestJson("/health");
  const platformRequest = platformEndpoint
    ? requestJson(platformEndpoint).catch(() => null)
    : Promise.resolve(null);

  Promise.all([healthRequest, platformRequest])
    .then(([health, platform]) => render(health, platform))
    .catch(() => {
      trigger.dataset.state = "unavailable";
      summary.textContent = "Live verification temporarily unavailable";
      badge.textContent = "Unknown";
      services.innerHTML =
        "<li><b>Status unavailable</b><span>The product remains usable; refresh to retry the stack check.</span></li>";
    });
})();