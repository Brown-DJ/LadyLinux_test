/* =====================================================
   LADY LINUX - MAIN CONTROLLER
   ===================================================== */

document.documentElement.setAttribute("data-ui-ready", "false");

function getCurrentPageKey() {
  return document.body.getAttribute("data-page") || "index";
}

function updateOverviewStatus(key, value) {
  const target = document.querySelector(`[data-status-key="${key}"]`);
  if (target) {
    target.textContent = value;
  }
}

/*
---------------------------------------------------------
Track whether the periodic telemetry refresh has started.
This avoids creating duplicate timers during re-initialization.
---------------------------------------------------------
*/
/*
---------------------------------------------------------
Update the status cards on the Unified Control Surface.
---------------------------------------------------------
*/
function updateStatusUI(cpu, memory, disk, firewall, users, theme) {
  const cpuElement = document.getElementById("cpuLoad");
  const memoryElement = document.getElementById("memoryUsage");
  const diskElement = document.getElementById("diskUsage");
  const firewallElement = document.getElementById("firewallStatus");
  const usersElement = document.getElementById("activeUsers");
  const themeElement = document.getElementById("currentTheme");

  // Populate placeholders once telemetry is available.
  if (cpuElement && cpu != null) cpuElement.textContent = cpu;
  if (memoryElement && memory != null) memoryElement.textContent = memory;
  if (diskElement && disk != null) diskElement.textContent = disk;
  // Firewall is optional in the current layout; update only if the element exists.
  if (firewallElement && firewall != null) firewallElement.textContent = firewall;
  if (usersElement && users != null) usersElement.textContent = users;
  if (themeElement && theme != null) themeElement.textContent = theme;
}

/*
Load system telemetry from the backend and update non-metric overview values.
*/
async function loadSystemTelemetry() {
  // Metric cards now subscribe through static/js/system_metrics.js.
  // Keep this loader as a no-op for the current layout to avoid duplicate fetches.
  if (getCurrentPageKey() !== "index") return;

  try {
    const themeKey = localStorage.getItem("lady-theme");
    const themeValue = typeof window.getThemeLabel === "function"
      ? window.getThemeLabel(themeKey || "Default")
      : (themeKey || "Unknown");

    updateStatusUI(null, null, null, null, null, themeValue);
  } catch (error) {
    console.error("Failed to load system telemetry:", error);
  }
}

/**
 * Legacy alias to preserve existing call sites while telemetry loader was
 * renamed to loadSystemTelemetry().
 */
async function loadSystemStatus() {
  await loadSystemTelemetry();
}

/*
Fetches services from backend and populates the Services table.
This only runs on the System page to avoid touching other views.
*/
async function loadServices() {
  if (getCurrentPageKey() !== "system") return;

  const table = document.querySelector("#services-table-body");
  if (!table) return;

  try {
    const response = await fetch("/api/system/services");
    if (!response.ok) {
      throw new Error(`Services API failed (${response.status})`);
    }

    const data = await response.json();
    table.innerHTML = "";

    (data.services || []).forEach((service) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${service.name}</td>
        <td>${service.status}</td>
        <td>-</td>
        <td>
          <button class="btn btn-sm btn-outline-secondary"
                  onclick="restartService('${service.name}')"
                  type="button">
            Restart
          </button>
        </td>
      `;
      table.appendChild(row);
    });
  } catch (error) {
    console.error("Failed to load services:", error);
    // Keep failure visible to users within the table region.
    table.innerHTML = '<tr><td colspan="4">Unable to load services.</td></tr>';
  }
}

/*
Triggers a service restart through backend endpoint and refreshes the table.
This helper is attached to window for inline button onclick support.
*/
async function restartService(name) {
  if (!name) return;

  try {
    await fetch(`/api/system/service/${encodeURIComponent(name)}/restart`, {
      method: "POST",
    });
  } catch (error) {
    console.error("Failed to restart service:", error);
  }

  await loadServices();
}

// Expose restartService globally because service rows call it via inline onclick.
window.restartService = restartService;

function updateThemeIndicator() {
  const themeEl = document.getElementById("currentTheme");
  if (!themeEl) return;

  const theme = localStorage.getItem("lady-theme") || "softcore";
  themeEl.textContent = theme === "soft" ? "softcore" : theme;
}

function applyThemeCssVars(cssVars) {
  Object.entries(cssVars || {}).forEach(([key, value]) => {
    document.documentElement.style.setProperty(key, value);
  });
}

function syncOverviewFromDocument() {
  const themeKey = localStorage.getItem("lady-theme");
  const theme = typeof window.getThemeLabel === "function"
    ? window.getThemeLabel(themeKey || "Default")
    : (themeKey || "Default");

  // Theme changes are local UI state, so keep theme text synchronized.
  updateOverviewStatus("theme", theme);
}

function applyActionSummary(detail = {}) {
  if (detail.action === "appearance.set_theme") {
    syncOverviewFromDocument();
  }
}

function initAccordionPanels() {
  const triggers = document.querySelectorAll("[data-accordion-trigger]");
  if (!triggers.length) return;

  triggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const targetId = trigger.getAttribute("data-accordion-target");
      const target = targetId ? document.getElementById(targetId) : null;
      if (!target) return;
      const shouldOpen = target.classList.contains("d-none");

      trigger.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
      const indicator = trigger.querySelector(".accordion-indicator");
      if (indicator) {
        indicator.innerHTML = shouldOpen ? "&#9660;" : "&#9654;";
      }

      target.classList.toggle("d-none", !shouldOpen);

      if (typeof window.logSystemActivity === "function") {
        const label = trigger.querySelector("span:last-child")?.textContent?.trim() || "Panel";
        window.logSystemActivity(`${label} ${target.classList.contains("d-none") ? "collapsed" : "expanded"}`);
      }
    });
  });
}

/**
 * Wire "You Can Ask" suggestion cards to the assistant input.
 *
 * Clicking a suggestion pre-fills the existing chat prompt field so users can
 * submit quickly without retyping common commands.
 */
function initAskSuggestions() {
  document.querySelectorAll(".ask-item").forEach((item) => {
    item.addEventListener("click", () => {
      const prompt = item.getAttribute("data-prompt") || "";
      const input = document.getElementById("ucsPrompt") || document.getElementById("prompt");

      if (input) {
        input.value = prompt;
        input.focus();
      }
    });
  });
}

async function initializeApp() {
  try {
    await initThemes();
    await loadNavigation();
    initAccordionPanels();
    initAskSuggestions();
    initChat();
    syncOverviewFromDocument();

    document.addEventListener("lady:overview-sync", syncOverviewFromDocument);
    document.addEventListener("lady:action-complete", (event) => {
      applyActionSummary(event.detail || {});
      syncOverviewFromDocument();
    });
    const handleThemeApplied = (e) => {
      const data = e.detail;

      if (!data) return;

      // support both formats
      const css = data.css || data.css_variables;

      if (css) {
        applyThemeCssVars(css);
      }

      const themeLabel = data.label || data.display_name || data.theme || "Custom";
      updateOverviewStatus("theme", themeLabel);
    };
    document.addEventListener("lady:theme-applied", handleThemeApplied);
    window.addEventListener("lady:theme-applied", handleThemeApplied);
  } catch (err) {
    console.error("Initialization error:", err);
  } finally {
    document.documentElement.setAttribute("data-ui-ready", "true");
  }
}

/*
---------------------------------------------------------
Run once the DOM is ready.
This ensures the page loads immediately and system data
loads asynchronously in the background.
---------------------------------------------------------
*/
window.addEventListener("DOMContentLoaded", () => {
  loadSystemTelemetry();
  loadServices();
  updateThemeIndicator();

  // Refresh service data whenever the Services tab becomes active.
  const servicesTabTrigger = document.getElementById("services-tab");
  if (servicesTabTrigger) {
    servicesTabTrigger.addEventListener("shown.bs.tab", () => {
      loadServices();
    });
  }

  setInterval(() => {
    updateThemeIndicator();
  }, 5000);
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeApp, { once: true });
} else {
  initializeApp();
}

async function loadNavigation() {
  const response = await fetch("/static/nav.html");
  const navMarkup = await response.text();

  const container = document.getElementById("nav-container");
  if (!container) return;

  container.innerHTML = navMarkup;

  const currentPath = window.location.pathname.replace(/\/+$/, "") || "/";
  container.querySelectorAll(".nav-link").forEach((link) => {
    const href = link.getAttribute("href");
    const normalizedHref = href.replace(/\/+$/, "") || "/";
    const isActive = normalizedHref === currentPath;

    link.classList.toggle("active", isActive);
    if (isActive) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
}


/* =====================================================
   THEME EVENT LISTENER
   Applies theme variables from backend theme events
   ===================================================== */

window.applyThemeCssVars = applyThemeCssVars;
