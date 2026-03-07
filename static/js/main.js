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
let systemRefreshStarted = false;

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
  if (cpuElement) cpuElement.textContent = cpu;
  if (memoryElement) memoryElement.textContent = memory;
  if (diskElement) diskElement.textContent = disk;
  // Firewall is optional in the current layout; update only if the element exists.
  if (firewallElement) firewallElement.textContent = firewall;
  if (usersElement) usersElement.textContent = users;
  if (themeElement) themeElement.textContent = theme;
}

/**
 * Formats byte values into readable units for disk telemetry.
 */
function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return "N/A";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  const precision = value >= 10 ? 0 : 1;
  return `${value.toFixed(precision)}${units[unitIndex]}`;
}

/*
Load system telemetry from the backend
and update dashboard UI values.
*/
async function loadSystemTelemetry() {
  // Only run telemetry polling on the Unified Control Surface page.
  if (getCurrentPageKey() !== "index") return;

  try {
    // Prefer the dedicated status endpoint.
    // Fallback to /api/system to remain compatible with deployments that
    // have not exposed /api/system/status yet.
    let response = await fetch("/api/system/status");
    if (!response.ok) {
      response = await fetch("/api/system");
    }
    if (!response.ok) {
      throw new Error(`System API failed (${response.status})`);
    }

    // Convert response to JSON.
    const data = await response.json();

    // The API wraps telemetry under "result"; keep fallbacks for resilience.
    const result = data && typeof data === "object" ? (data.result || {}) : {};
    const platform = result && typeof result === "object" ? (result.platform || {}) : {};
    const disk = result && typeof result === "object" ? (result.disk || {}) : {};
    const env = result && typeof result === "object" ? (result.env || {}) : {};
    const firewall = result && typeof result === "object" ? (result.firewall || {}) : {};

    // Compute display values with graceful fallbacks when fields are unavailable.
    const cpuValue = data.cpu_load || data.cpu || platform.processor || "N/A";
    const memoryValue = data.memory_usage || data.memory || "N/A";
    const diskUsed = formatBytes(disk.used_bytes);
    const diskTotal = formatBytes(disk.total_bytes);
    const diskValue =
      data.disk_usage ||
      data.disk ||
      (diskUsed !== "N/A" && diskTotal !== "N/A" ? `${diskUsed} / ${diskTotal}` : "N/A");
    const firewallValue = data.firewall || firewall.active || "Unknown";
    const usersValue = data.users || env.user || "N/A";
    const themeKey = localStorage.getItem("lady-theme");
    const themeValue = data.theme || (typeof window.getThemeLabel === "function"
      ? window.getThemeLabel(themeKey || "Default")
      : (themeKey || "Unknown"));

    // Update dashboard elements with returned values.
    updateStatusUI(cpuValue, memoryValue, diskValue, firewallValue, usersValue, themeValue);
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

  const theme = localStorage.getItem("lady-theme") || "soft";
  themeEl.textContent = theme;
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
    document.addEventListener("lady:theme-applied", (event) => {
      const themeLabel = event.detail?.label || event.detail?.theme || "Custom";
      updateOverviewStatus("theme", themeLabel);
    });
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

  /**
   * Periodically refresh system telemetry so the dashboard
   * reflects real-time system state.
   */
  if (!systemRefreshStarted) {
    systemRefreshStarted = true;
    setInterval(() => {
      loadSystemTelemetry();
      updateThemeIndicator();
    }, 5000);
  }
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
