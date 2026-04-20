/*
 * Fetches and renders Google Calendar, Gmail, and Fit cards on the dashboard.
 */

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatCacheAge(seconds) {
  if (seconds === null || seconds === undefined) return "";
  if (seconds < 60) return "Updated just now";
  if (seconds < 3600) return `Updated ${Math.floor(seconds / 60)} min ago`;
  return `Updated ${Math.floor(seconds / 3600)} hr ago`;
}

function formatEventTime(isoStr) {
  try {
    return new Date(isoStr).toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return isoStr;
  }
}

let _authStatusCache = null;

async function isGoogleAuthorized() {
  if (_authStatusCache !== null) return _authStatusCache;
  try {
    const res = await fetch("/api/google/oauth/status", { cache: "no-store" });
    const data = await res.json();
    _authStatusCache = data.authorized === true;
  } catch {
    _authStatusCache = false;
  }
  return _authStatusCache;
}

async function isHealthAuthorized() {
  try {
    const res = await fetch("/api/google/health/oauth/status", { cache: "no-store" });
    const data = await res.json();
    return data.authorized === true;
  } catch {
    return false;
  }
}

function showLoading(topic) {
  document.getElementById(`${topic}-loading`)?.classList.remove("d-none");
  document.getElementById(`${topic}-auth-prompt`)?.classList.add("d-none");
}

function hideLoading(topic) {
  document.getElementById(`${topic}-loading`)?.classList.add("d-none");
}

function showAuthPrompt(topic) {
  document.getElementById(`${topic}-auth-prompt`)?.classList.remove("d-none");
  document.getElementById(`${topic}-loading`)?.classList.add("d-none");
}

async function loadCalendarCard() {
  const list = document.getElementById("calendar-event-list");
  const cacheEl = document.getElementById("calendar-cache-age");
  if (!list) return;

  const authed = await isGoogleAuthorized();
  if (!authed) {
    showAuthPrompt("calendar");
    return;
  }

  showLoading("calendar");

  try {
    const res = await fetch("/api/google/calendar/today", { cache: "no-store" });
    const data = await res.json();
    hideLoading("calendar");

    const events = data.events || [];
    if (!events.length) {
      list.innerHTML = `
        <li class="text-muted small py-2 text-center">
          <i class="bi bi-calendar-check me-1"></i>No events today
        </li>`;
      return;
    }

    list.innerHTML = events.map((event) => {
      const time = event.all_day
        ? `<span class="badge bg-secondary me-1" style="font-size:0.6rem">All day</span>`
        : `<span class="text-muted me-1" style="font-size:0.72rem">${formatEventTime(event.start)}</span>`;
      const location = event.location
        ? `<div class="text-muted" style="font-size:0.68rem">
             <i class="bi bi-geo-alt me-1"></i>${escapeHtml(event.location)}
           </div>`
        : "";

      return `
        <li class="mb-2 pb-2 border-bottom border-secondary">
          ${time}
          <span class="small fw-medium">${escapeHtml(event.title)}</span>
          ${location}
        </li>`;
    }).join("");

    if (cacheEl) cacheEl.textContent = formatCacheAge(data.cache_age);
  } catch (err) {
    hideLoading("calendar");
    list.innerHTML = `
      <li class="text-muted small text-center py-2">
        <i class="bi bi-exclamation-circle me-1"></i>Failed to load
      </li>`;
    console.warn("Calendar card error:", err);
  }
}

async function loadGmailCard() {
  const list = document.getElementById("gmail-message-list");
  const badge = document.getElementById("gmail-unread-badge");
  const cacheEl = document.getElementById("gmail-cache-age");
  if (!list) return;

  const authed = await isGoogleAuthorized();
  if (!authed) {
    showAuthPrompt("gmail");
    return;
  }

  showLoading("gmail");

  try {
    const res = await fetch("/api/google/gmail/inbox", { cache: "no-store" });
    const data = await res.json();
    hideLoading("gmail");

    const messages = data.messages || [];
    const unreadCount = data.unread_count || 0;

    if (badge) {
      if (unreadCount > 0) {
        badge.textContent = unreadCount;
        badge.classList.remove("d-none");
      } else {
        badge.classList.add("d-none");
      }
    }

    if (!messages.length) {
      list.innerHTML = `
        <li class="text-muted small py-2 text-center">
          <i class="bi bi-inbox me-1"></i>No unread messages
        </li>`;
      return;
    }

    list.innerHTML = messages.map((message) => {
      const sender = message.from?.includes("<")
        ? escapeHtml(message.from.split("<")[0].trim())
        : escapeHtml(message.from || "Unknown");

      return `
        <li class="mb-2 pb-2 border-bottom border-secondary">
          <div class="small fw-medium text-truncate" style="max-width:100%">
            ${escapeHtml(message.subject || "No subject")}
          </div>
          <div class="text-muted" style="font-size:0.72rem">
            <i class="bi bi-person me-1"></i>${sender}
          </div>
        </li>`;
    }).join("");

    if (cacheEl) cacheEl.textContent = formatCacheAge(data.cache_age);
  } catch (err) {
    hideLoading("gmail");
    list.innerHTML = `
      <li class="text-muted small text-center py-2">
        <i class="bi bi-exclamation-circle me-1"></i>Failed to load
      </li>`;
    console.warn("Gmail card error:", err);
  }
}

async function loadFitCard() {
  const cacheEl = document.getElementById("fit-cache-age");
  const fitData = document.getElementById("fit-data");
  if (!fitData) return;

  const authed = await isHealthAuthorized();
  if (!authed) {
    showAuthPrompt("fit");
    return;
  }

  showLoading("fit");

  try {
    const res = await fetch("/api/google/fit/today", { cache: "no-store" });
    const data = await res.json();
    hideLoading("fit");

    const d = data.data || {};
    const steps = d.steps || 0;
    const goalPct = Math.min(Math.round((steps / 10000) * 100), 100);
    const stepsEl = document.getElementById("fit-steps");
    const stepsBar = document.getElementById("fit-steps-bar");
    const stepsGoal = document.getElementById("fit-steps-goal");

    if (stepsEl) stepsEl.textContent = steps.toLocaleString();
    if (stepsBar) stepsBar.style.width = `${goalPct}%`;
    if (stepsGoal) stepsGoal.textContent = `${steps.toLocaleString()} / 10,000 goal`;

    const calEl = document.getElementById("fit-calories");
    if (calEl) calEl.textContent = d.calories ? `${Math.round(d.calories)} kcal` : "--";

    const activeEl = document.getElementById("fit-active");
    if (activeEl) activeEl.textContent = d.active_minutes ? `${d.active_minutes} min` : "--";

    const sleepEl = document.getElementById("fit-sleep");
    if (sleepEl) {
      if (d.sleep_minutes) {
        const h = Math.floor(d.sleep_minutes / 60);
        const m = d.sleep_minutes % 60;
        sleepEl.textContent = `${h}h ${m}m`;
      } else {
        sleepEl.textContent = "--";
      }
    }

    const heartEl = document.getElementById("fit-heart");
    if (heartEl) heartEl.textContent = d.heart_rate_avg ? `${Math.round(d.heart_rate_avg)} bpm` : "--";

    if (cacheEl) cacheEl.textContent = formatCacheAge(data.cache_age);
  } catch (err) {
    hideLoading("fit");
    fitData.innerHTML = `
      <div class="text-muted small text-center py-2">
        <i class="bi bi-exclamation-circle me-1"></i>Failed to load
      </div>`;
    console.warn("Fit card error:", err);
  }
}

document.querySelectorAll(".ll-google-refresh").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const topic = btn.getAttribute("data-google-topic");
    if (!topic) return;

    const icon = btn.querySelector("i");
    if (icon) icon.classList.add("spin");
    btn.disabled = true;

    try {
      await fetch(`/api/google/${topic}/refresh`, { method: "POST" });
    } catch {
      // Card reload below will surface any persistent failure.
    }

    if (topic === "calendar") await loadCalendarCard();
    if (topic === "gmail") await loadGmailCard();
    if (topic === "fit") await loadFitCard();

    if (icon) icon.classList.remove("spin");
    btn.disabled = false;
  });
});

document.addEventListener("DOMContentLoaded", () => {
  loadCalendarCard();
  loadGmailCard();
  loadFitCard();
});
