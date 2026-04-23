/**
 * static/js/nav_controls.js
 *
 * Handles the navbar dark/light toggle and notification dropdown.
 * Depends on: themes.js (window.applyTheme must be available).
 * Load order: after themes.js, after DOMContentLoaded fires.
 */

(function () {
  "use strict";

  /* ── Theme toggle ─────────────────────────────────────────── */

  // The two named themes used for the quick toggle.
  // Change these keys to match whichever themes you want to swap.
  const DARK_THEME  = "terminal";
  const LIGHT_THEME = "softcore";

  // localStorage key shared with themes.js
  const LS_THEME_KEY = "lady-theme";

  const themeBtn  = document.getElementById("navThemeToggle");
  const themeIcon = document.getElementById("navThemeIcon");

   * Update the navbar icon to reflect the currently active theme.
   * Moon = currently dark (click to go light); Sun = currently light (click to go dark).
   */
  function syncThemeIcon(activeTheme) {
    if (!themeIcon) return;
    const isDark = activeTheme === DARK_THEME;
    themeIcon.className = isDark
      ? "bi bi-sun-fill"           // dark mode active → show sun (switch to light)
      : "bi bi-moon-stars-fill";   // light mode active → show moon (switch to dark)
  }

   * Sync BOTH the navbar icon and the radial spoke icon to reflect active theme.
   * Called on toggle and on page load.
   */
  function syncAllThemeIcons(activeTheme) {
    syncThemeIcon(activeTheme);

    const spokeIcon = document.querySelector("#ladySpokeTheme i");
    if (spokeIcon) {
      const isDark = activeTheme === DARK_THEME;
      spokeIcon.className = isDark ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
    }
  }

  /**
   * Toggle between dark and light named themes.
   * Delegates to window.applyTheme without syncing to the backend.
   */
  function handleThemeToggle() {
    if (typeof window.applyTheme !== "function") {
      console.warn("[nav_controls] window.applyTheme not available");
      return;
    }

    const current = localStorage.getItem(LS_THEME_KEY) || DARK_THEME;
    const next = current === DARK_THEME ? LIGHT_THEME : DARK_THEME;

    window.applyTheme(next, { remote: false, persist: true });
    localStorage.setItem(LS_THEME_KEY, next);
    syncAllThemeIcons(next);
  }

  if (themeBtn) {
    themeBtn.addEventListener("click", handleThemeToggle);

    // Sync both icons on page load — short delay so restoreTheme() runs first
    setTimeout(() => {
      const saved = localStorage.getItem(LS_THEME_KEY) || DARK_THEME;
      syncAllThemeIcons(saved);
    }, 100);
  }

  // Expose for global.js spoke wiring
  window.handleThemeToggle = handleThemeToggle;
  window.syncAllThemeIcons = syncAllThemeIcons;


  /* ── Notification dropdown ────────────────────────────────── */

  const notifList      = document.getElementById("navNotifList");
  const notifEmpty     = document.getElementById("navNotifEmpty");
  const notifBadge     = document.getElementById("navNotifBadge");
  const notifMarkRead  = document.getElementById("navNotifMarkRead");

  let notifications = [];

  const NOTIF_POLL_MS = 60_000;
  const readIds = new Set();
  const THRESHOLDS = {
    cpu:    { warning: 85, critical: 95 },
    memory: { warning: 85, critical: 95 },
    disk:   { warning: 80, critical: 90 },
  };

  function alertId(type) {
    return `alert-${type}`;
  }

  function buildNotifications(metrics, services) {
    const items = [];
    const now = "just now";

    if (metrics?.cpu_load > THRESHOLDS.cpu.critical) {
      const id = alertId("cpu-crit");
      items.push({ id, icon: "bi-cpu-fill", text: `CPU critical - ${Math.round(metrics.cpu_load)}% utilization`, sub: now, href: "/os", read: readIds.has(id) });
    } else if (metrics?.cpu_load > THRESHOLDS.cpu.warning) {
      const id = alertId("cpu-warn");
      items.push({ id, icon: "bi-cpu", text: `CPU high - ${Math.round(metrics.cpu_load)}% utilization`, sub: now, href: "/os", read: readIds.has(id) });
    }

    if (metrics?.memory_usage > THRESHOLDS.memory.critical) {
      const id = alertId("mem-crit");
      items.push({ id, icon: "bi-memory", text: `Memory critical - ${Math.round(metrics.memory_usage)}% used`, sub: now, href: "/os", read: readIds.has(id) });
    } else if (metrics?.memory_usage > THRESHOLDS.memory.warning) {
      const id = alertId("mem-warn");
      items.push({ id, icon: "bi-memory", text: `Memory high - ${Math.round(metrics.memory_usage)}% used`, sub: now, href: "/os", read: readIds.has(id) });
    }

    if (metrics?.disk_usage > THRESHOLDS.disk.critical) {
      const id = alertId("disk-crit");
      items.push({ id, icon: "bi-hdd-fill", text: `Disk critical - ${Math.round(metrics.disk_usage)}% used`, sub: now, href: "/os", read: readIds.has(id) });
    } else if (metrics?.disk_usage > THRESHOLDS.disk.warning) {
      const id = alertId("disk-warn");
      items.push({ id, icon: "bi-hdd", text: `Disk high - ${Math.round(metrics.disk_usage)}% used`, sub: now, href: "/os", read: readIds.has(id) });
    }

    const relevant = Array.isArray(services)
      ? services.filter((service) =>
          typeof window.isRelevantService === "function"
            ? window.isRelevantService(service)
            : true
        )
      : [];
    const failed = relevant.filter(
      (service) => String(service.status || "").toLowerCase() === "failed"
    );

    if (failed.length === 1) {
      const id = alertId(`svc-${failed[0].name}`);
      items.push({ id, icon: "bi-gear-fill", text: `Service ${failed[0].name} has failed`, sub: now, href: "/os", read: readIds.has(id) });
    } else if (failed.length > 1) {
      const id = alertId("svc-multi");
      items.push({ id, icon: "bi-gear-fill", text: `${failed.length} services have failed`, sub: now, href: "/os", read: readIds.has(id) });
    }

    return items;
  }

  async function pollNotifications() {
    try {
      const [mRes, sRes] = await Promise.all([
        fetch("/api/system/metrics", { cache: "no-store" }),
        fetch("/api/system/services", { cache: "no-store" }),
      ]);

      const metrics = mRes.ok ? await mRes.json() : null;
      const services = sRes.ok ? await sRes.json() : [];
      const svcList = Array.isArray(services)
        ? services
        : (services?.services ?? []);

      notifications = buildNotifications(metrics, svcList);
      renderNotifications();
    } catch (err) {
      console.warn("[nav_controls] notification poll failed:", err);
    }
  }

  /** Build and render all notification list items into #navNotifList */
  function renderNotifications() {
    if (!notifList) return;

    const unread = notifications.filter((n) => !n.read);

    // Toggle empty-state visibility
    if (notifEmpty) notifEmpty.classList.toggle("d-none", notifications.length > 0);

    // Update badge
    if (notifBadge) {
      if (unread.length > 0) {
        notifBadge.textContent = unread.length;
        notifBadge.classList.remove("d-none");
      } else {
        notifBadge.classList.add("d-none");
      }
    }

    // Clear existing items before re-render
    notifList.innerHTML = "";

    notifications.forEach((item) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <a
          class="dropdown-item d-flex align-items-start gap-2 py-2 ${item.read ? "opacity-50" : ""}"
          href="${item.href || '#'}"
          data-notif-id="${item.id}"
          style="font-size: 0.82rem; white-space: normal;"
        >
          <!-- Icon col -->
          <i class="bi ${item.icon} mt-1 flex-shrink-0" style="color: var(--accent);"></i>
          <!-- Text col -->
          <div class="flex-grow-1 min-width-0">
            <div class="fw-semibold lh-sm">${item.text}</div>
            <div class="text-muted" style="font-size: 0.72rem;">${item.sub}</div>
          </div>
          <!-- Unread dot -->
          ${!item.read ? '<span class="flex-shrink-0 rounded-circle ms-1 mt-1" style="width:6px;height:6px;background:var(--accent);display:inline-block;"></span>' : ""}
        </a>`;

      // Mark individual item as read on click
      li.querySelector("a").addEventListener("click", () => {
        readIds.add(item.id);
        item.read = true;
        renderNotifications();   // re-render badge + items
      });

      notifList.appendChild(li);
    });
  }

  /** Mark all notifications read */
  if (notifMarkRead) {
    notifMarkRead.addEventListener("click", (e) => {
      e.preventDefault();
      notifications.forEach((n) => readIds.add(n.id));
      notifications.forEach((n) => (n.read = true));
      renderNotifications();
    });
  }

  pollNotifications();
  setInterval(pollNotifications, NOTIF_POLL_MS);

}());
