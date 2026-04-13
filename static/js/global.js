function toggleFullscreen() {
  const doc = document.documentElement;

  if (!document.fullscreenElement) {
    doc.requestFullscreen().catch((err) => {
      console.error("Fullscreen error:", err);
    });
  } else {
    document.exitFullscreen?.();
  }
}

function syncFullscreenUI() {
  const isFull = Boolean(document.fullscreenElement);

  document.querySelectorAll("[data-fullscreen]").forEach((button) => {
    const mode = button.getAttribute("data-fullscreen-label");
    button.textContent = mode === "text" ? (isFull ? "Exit Fullscreen" : "Fullscreen") : (isFull ? "Exit" : "FS");
    button.title = isFull ? "Exit Fullscreen" : "Fullscreen";
  });
}


document.addEventListener("fullscreenchange", syncFullscreenUI);

document.addEventListener("DOMContentLoaded", () => {
  syncFullscreenUI();

  document.querySelectorAll("[data-fullscreen]").forEach((button) => {
    button.addEventListener("click", toggleFullscreen);
  });

  // -- Widget: Orb + Expand tray ------------------------------------------------
  // ladyRadialRoot ID kept on the root div for outside-click compatibility
  const radialRoot    = document.getElementById("ladyRadialRoot");
  const ladyBtn       = document.getElementById("ladyBtn");
  const ladyPanel     = document.getElementById("ladyPanel");
  const ladyClose     = document.getElementById("ladyClose");
  const ladyExpandBtn = document.getElementById("ladyExpandBtn");
  const utilityTray   = document.getElementById("ladyUtilityTray");

  // Orb click -> open console panel immediately (primary action)
  if (ladyBtn && ladyPanel) {
    ladyBtn.addEventListener("click", () => {
      const isHidden = ladyPanel.classList.toggle("hidden");
      ladyPanel.setAttribute("aria-hidden", String(isHidden));

      // Close tray when opening panel for a cleaner UX
      if (!isHidden && utilityTray) {
        utilityTray.classList.remove("is-open");
        ladyExpandBtn?.classList.remove("is-open");
        utilityTray.setAttribute("aria-hidden", "true");
      }
    });
  }

  // Close button - collapses panel only
  if (ladyClose && ladyPanel) {
    ladyClose.addEventListener("click", () => {
      ladyPanel.classList.add("hidden");
      ladyPanel.setAttribute("aria-hidden", "true");
    });
  }

  // Expand button -> toggles utility tray
  if (ladyExpandBtn && utilityTray) {
    ladyExpandBtn.addEventListener("click", () => {
      const isOpen = utilityTray.classList.toggle("is-open");
      ladyExpandBtn.classList.toggle("is-open", isOpen);
      utilityTray.setAttribute("aria-hidden", String(!isOpen));
    });
  }

  // Theme util button - delegates to nav_controls.js handleThemeToggle
  const ladySpokeTheme = document.getElementById("ladySpokeTheme");
  if (ladySpokeTheme) {
    ladySpokeTheme.addEventListener("click", () => {
      if (typeof window.handleThemeToggle === "function") {
        window.handleThemeToggle();
      } else {
        // Fallback: click nav toggle directly
        document.getElementById("navThemeToggle")?.click();
      }
    });
  }

  // Metrics util button - calls shared fetchMetrics if available
  const ladySpokeMetrics = document.getElementById("ladySpokeMetrics");
  if (ladySpokeMetrics) {
    ladySpokeMetrics.addEventListener("click", () => {
      if (typeof window.fetchMetrics === "function") window.fetchMetrics();
    });
  }

  // Outside-click: close both tray and panel when clicking away from widget
  document.addEventListener("click", (e) => {
    if (
      radialRoot &&
      ladyPanel &&
      !radialRoot.contains(e.target) &&
      !ladyPanel.contains(e.target)
    ) {
      // Close tray
      utilityTray?.classList.remove("is-open");
      ladyExpandBtn?.classList.remove("is-open");
      utilityTray?.setAttribute("aria-hidden", "true");

      // Do NOT auto-close panel on outside click (intentional - keeps convo visible)
    }
  });
});

window.toggleFullscreen = toggleFullscreen;

// ── Context Nav Collapse Toggle ──────────────────────────────
(function initContextNavCollapse() {
  const STORAGE_KEY = "lady-context-nav-collapsed";
  const btn = document.getElementById("contextNavToggle");
  const links = document.getElementById("contextNavLinks");
  if (!btn || !links) return;

  // Restore saved state
  if (localStorage.getItem(STORAGE_KEY) === "true") {
    links.classList.add("context-nav-collapsed");
    btn.classList.add("context-nav-is-collapsed");
  }

  btn.addEventListener("click", () => {
    const isNowCollapsed = links.classList.toggle("context-nav-collapsed");
    btn.classList.toggle("context-nav-is-collapsed", isNowCollapsed);
    localStorage.setItem(STORAGE_KEY, String(isNowCollapsed));
  });
})();
