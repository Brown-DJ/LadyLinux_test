/* =====================================================
   LADY LINUX - DASHBOARD METRICS POLLING
   ===================================================== */

(function () {
  const POLL_INTERVAL_MS = 5000;
  let metricsTimerStarted = false;

  function onIndexPage() {
    return document.body?.getAttribute("data-page") === "index";
  }

  function extractPercent(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return Math.max(0, Math.min(100, value));
    }

    if (typeof value === "string") {
      const match = value.match(/(\d+(?:\.\d+)?)/);
      if (match) {
        return Math.max(0, Math.min(100, Number(match[1])));
      }
    }

    return null;
  }

  function calculateDiskPercent(disk) {
    if (!disk || typeof disk !== "object") return null;
    const used = Number(disk.used_bytes);
    const total = Number(disk.total_bytes);

    if (!Number.isFinite(used) || !Number.isFinite(total) || total <= 0) {
      return null;
    }

    return Math.max(0, Math.min(100, (used / total) * 100));
  }

  function updateMetric(valueId, barId, percent) {
    const valueEl = document.getElementById(valueId);
    const barEl = document.getElementById(barId);

    if (!valueEl || !barEl) return;

    if (percent === null) {
      valueEl.textContent = "N/A";
      barEl.style.width = "0%";
      barEl.setAttribute("aria-valuenow", "0");
      return;
    }

    const rounded = Math.round(percent);
    valueEl.textContent = `${rounded}%`;
    barEl.style.width = `${rounded}%`;
    barEl.setAttribute("aria-valuenow", String(rounded));

    const wrapper = barEl.closest(".progress");
    if (wrapper) {
      wrapper.setAttribute("aria-valuenow", String(rounded));
    }
  }

  async function fetchAndRenderMetrics() {
    if (!onIndexPage()) return;

    try {
      const response = await fetch("/api/system/status", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`System status request failed (${response.status})`);
      }

      const payload = await response.json();
      const result = payload?.result || {};

      const cpu = extractPercent(payload?.cpu_load ?? payload?.cpu);
      const memory = extractPercent(payload?.memory_usage ?? payload?.memory);
      const disk = extractPercent(payload?.disk_usage ?? payload?.disk) ?? calculateDiskPercent(result?.disk);

      updateMetric("cpuLoad", "cpuProgress", cpu);
      updateMetric("memoryUsage", "memoryProgress", memory);
      updateMetric("diskUsage", "diskProgress", disk);
    } catch (error) {
      console.error("Dashboard metric polling failed:", error);
    }
  }

  function startMetricsPolling() {
    if (metricsTimerStarted || !onIndexPage()) return;

    metricsTimerStarted = true;

    // Poll backend every 5 seconds so dashboard cards reflect current status.
    // Immediate first call avoids waiting for the first interval tick.
    fetchAndRenderMetrics();
    setInterval(fetchAndRenderMetrics, POLL_INTERVAL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startMetricsPolling, { once: true });
  } else {
    startMetricsPolling();
  }
})();
