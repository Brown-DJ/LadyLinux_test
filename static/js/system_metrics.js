const POLL_INTERVAL = 5000;
const METRICS_ENDPOINT = "/api/system/status";
const listeners = [];

let lastMetrics = null;
let pollerPromise = null;

function emitMetrics(metrics) {
  lastMetrics = metrics;

  listeners.slice().forEach((listener) => {
    try {
      listener(metrics);
    } catch (error) {
      console.error("metrics listener error", error);
    }
  });

  if (window.eventBus && typeof window.eventBus.emit === "function") {
    window.eventBus.emit("metrics:update", metrics);
  }
}

function normalizePercentage(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  return Math.max(0, Math.min(100, numeric));
}

function buildMetrics(payload = {}) {
  const memoryUsed = Number(payload.memory_used);
  const memoryTotal = Number(payload.memory_total);
  const diskUsed = Number(payload.disk_used);
  const diskTotal = Number(payload.disk_total);

  return {
    ...payload,
    cpu_load: normalizePercentage(payload.cpu_load ?? payload.cpu),
    memory_usage: normalizePercentage(
      payload.memory_usage
      ?? (Number.isFinite(memoryUsed) && Number.isFinite(memoryTotal) && memoryTotal > 0
        ? (memoryUsed / memoryTotal) * 100
        : null)
    ),
    disk_usage: normalizePercentage(
      payload.disk_usage
      ?? (Number.isFinite(diskUsed) && Number.isFinite(diskTotal) && diskTotal > 0
        ? (diskUsed / diskTotal) * 100
        : null)
    ),
  };
}

async function fetchMetrics() {
  try {
    const response = await fetch(METRICS_ENDPOINT, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    emitMetrics(buildMetrics(payload));
  } catch (error) {
    console.error("metrics error", error);
  }
}

function startPolling() {
  if (window.__LL_METRICS_RUNNING) return;

  window.__LL_METRICS_RUNNING = true;
  pollerPromise = fetchMetrics();
  window.setInterval(fetchMetrics, POLL_INTERVAL);
}

export function subscribe(listener) {
  if (typeof listener !== "function") {
    throw new TypeError("subscribe(listener) requires a function");
  }

  listeners.push(listener);

  if (lastMetrics) {
    listener(lastMetrics);
  } else if (!window.__LL_METRICS_RUNNING && pollerPromise === null) {
    startPolling();
  }

  return () => {
    const index = listeners.indexOf(listener);
    if (index >= 0) {
      listeners.splice(index, 1);
    }
  };
}

export function getLatestMetrics() {
  return lastMetrics;
}

startPolling();
