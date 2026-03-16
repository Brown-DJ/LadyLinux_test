import { subscribe } from "./ui_event_bus.js";

const ALERT_SEVERITY_RANK = {
  info: 0,
  warning: 1,
  critical: 2,
};

let latestMetrics = null;
let latestServices = [];

function formatPercent(value) {
  return Number.isFinite(value) ? `${Math.round(value)}%` : "N/A";
}

function formatBytes(bytes) {
  const numeric = Number(bytes);
  if (!Number.isFinite(numeric) || numeric < 0) return "N/A";

  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let value = numeric;
  let index = 0;

  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }

  const decimals = value >= 10 ? 0 : 1;
  return `${value.toFixed(decimals)} ${units[index]}`;
}

function formatUptime(seconds) {
  const numeric = Number(seconds);
  if (!Number.isFinite(numeric) || numeric < 0) return "N/A";

  const days = Math.floor(numeric / 86400);
  const hours = Math.floor((numeric % 86400) / 3600);
  const minutes = Math.floor((numeric % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function formatLoadAverage(loadAvg) {
  if (!Array.isArray(loadAvg) || loadAvg.length === 0) return "N/A";
  const values = loadAvg
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value))
    .map((value) => value.toFixed(2));
  return values.length ? values.join(" / ") : "N/A";
}

function formatCompactNetwork(rx, tx) {
  return `RX ${formatBytes(rx)} | TX ${formatBytes(tx)}`;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function focusSystemTab(tabId) {
  const trigger = tabId ? document.getElementById(tabId) : null;
  if (!trigger) return;

  if (window.bootstrap?.Tab) {
    window.bootstrap.Tab.getOrCreateInstance(trigger).show();
  } else {
    trigger.click();
  }

  trigger.focus();
}

function initStatusBarNavigation() {
  document.querySelectorAll("[data-status-target]").forEach((element) => {
    element.addEventListener("click", () => {
      focusSystemTab(element.getAttribute("data-status-target"));
    });
  });
}

function setProgress(id, value) {
  const progress = document.getElementById(id);
  if (!progress) return;

  const width = Number.isFinite(value) ? Math.round(value) : 0;
  progress.style.width = `${width}%`;
  progress.setAttribute("aria-valuenow", String(width));

  const wrapper = progress.closest(".progress");
  if (wrapper) {
    wrapper.setAttribute("aria-valuenow", String(width));
  }
}

function removeSkeletons() {
  document.querySelectorAll(".metric-skeleton").forEach((element) => element.remove());
}

function renderMetrics(data) {
  removeSkeletons();

  setText("cpuLoadOS", formatPercent(data.cpu_load));
  setText("cpuMetaOS", `Load average: ${formatLoadAverage(data.load_avg)}`);
  setProgress("cpuProgressOS", data.cpu_load);

  setText("memoryUsageOS", formatPercent(data.memory_usage));
  setText("memoryMetaOS", `${formatBytes(data.memory_used)} / ${formatBytes(data.memory_total)} used`);
  setProgress("memoryProgressOS", data.memory_usage);

  setText("diskUsageOS", formatPercent(data.disk_usage));
  setText("diskMetaOS", `${formatBytes(data.disk_used)} / ${formatBytes(data.disk_total)} used`);
  setProgress("diskProgressOS", data.disk_usage);

  setText("processCountOS", Number.isFinite(Number(data.process_count)) ? `${data.process_count}` : "N/A");
  setText("processMetaOS", "Running processes");

  setText("networkRxOS", formatBytes(data.network_rx));
  setText("networkTxOS", formatBytes(data.network_tx));

  setText("uptimeOS", formatUptime(data.uptime));
  setText("systemMetaOS", `${data.platform || "Unknown"} | ${data.arch || "Unknown"}`);
}

function renderStatusBar(metrics) {
  setText("globalCpuStatus", formatPercent(metrics.cpu_load));
  setText("globalMemoryStatus", formatPercent(metrics.memory_usage));
  setText("globalDiskStatus", formatPercent(metrics.disk_usage));
  setText("globalNetworkStatus", formatCompactNetwork(metrics.network_rx, metrics.network_tx));
  setText("globalUptimeStatus", formatUptime(metrics.uptime));
}

// Alert thresholds are intentionally centralized so the System page has one
// clear place to evolve health rules as the control center grows.
function collectMetricAlerts(metrics) {
  const alerts = [];

  if (Number.isFinite(metrics.cpu_load)) {
    if (metrics.cpu_load > 95) {
      alerts.push({ level: "critical", message: `CPU usage is critically high (${Math.round(metrics.cpu_load)}%).`, targetTab: "metrics-tab" });
    } else if (metrics.cpu_load > 85) {
      alerts.push({ level: "warning", message: `CPU usage is elevated (${Math.round(metrics.cpu_load)}%).`, targetTab: "metrics-tab" });
    }
  }

  if (Number.isFinite(metrics.memory_usage)) {
    if (metrics.memory_usage > 95) {
      alerts.push({ level: "critical", message: `Memory usage is critically high (${Math.round(metrics.memory_usage)}%).`, targetTab: "metrics-tab" });
    } else if (metrics.memory_usage > 85) {
      alerts.push({ level: "warning", message: `Memory usage is elevated (${Math.round(metrics.memory_usage)}%).`, targetTab: "metrics-tab" });
    }
  }

  if (Number.isFinite(metrics.disk_usage)) {
    if (metrics.disk_usage > 90) {
      alerts.push({ level: "critical", message: `Disk usage is critically high (${Math.round(metrics.disk_usage)}%).`, targetTab: "storage-tab" });
    } else if (metrics.disk_usage > 80) {
      alerts.push({ level: "warning", message: `Disk usage is at ${Math.round(metrics.disk_usage)}%.`, targetTab: "storage-tab" });
    }
  }

  return alerts;
}

function collectServiceAlert(services) {
  if (!Array.isArray(services) || services.length === 0) return null;

  const badServices = services.filter((service) => ["dead", "failed", "unknown"].includes(String(service.status || "").toLowerCase()));
  if (!badServices.length) return null;

  return {
    level: "warning",
    message: badServices.length === 1
      ? `Service ${badServices[0].name} requires attention (${badServices[0].status}).`
      : `${badServices.length} services require attention.`,
    targetTab: "services-tab",
  };
}

function getTopPriorityAlert(metrics, services) {
  const alerts = [...collectMetricAlerts(metrics)];
  const serviceAlert = collectServiceAlert(services);

  if (serviceAlert) {
    alerts.push(serviceAlert);
  }

  if (!alerts.length) return null;

  return alerts.sort((a, b) => ALERT_SEVERITY_RANK[b.level] - ALERT_SEVERITY_RANK[a.level])[0];
}

function renderHealthBanner(metrics, services) {
  const banner = document.getElementById("systemHealthBanner");
  const level = document.getElementById("systemHealthBannerLevel");
  const message = document.getElementById("systemHealthBannerMessage");
  if (!banner || !level || !message) return;

  const alert = getTopPriorityAlert(metrics, services);
  if (!alert) {
    banner.classList.add("d-none");
    banner.setAttribute("aria-hidden", "true");
    banner.removeAttribute("data-level");
    banner.removeAttribute("data-target-tab");
    return;
  }

  banner.classList.remove("d-none");
  banner.setAttribute("aria-hidden", "false");
  banner.setAttribute("data-level", alert.level);
  banner.setAttribute("data-target-tab", alert.targetTab || "");
  level.textContent = alert.level.toUpperCase();
  message.textContent = alert.message;
}

function updateSystemHealthUI() {
  if (!latestMetrics) return;

  renderStatusBar(latestMetrics);
  renderHealthBanner(latestMetrics, latestServices);
}

function initHealthBannerNavigation() {
  const banner = document.getElementById("systemHealthBanner");
  if (!banner) return;

  banner.addEventListener("click", () => {
    focusSystemTab(banner.getAttribute("data-target-tab"));
  });
}

function renderOSMetrics(data) {
  if (document.body?.getAttribute("data-page") !== "system") return;
  latestMetrics = data;
  renderMetrics(data);
  updateSystemHealthUI();
}

initStatusBarNavigation();
initHealthBannerNavigation();

subscribe("metrics:update", (metrics) => {
  renderOSMetrics(metrics);
});

subscribe("services:update", (services) => {
  if (document.body?.getAttribute("data-page") !== "system") return;
  latestServices = Array.isArray(services) ? services : [];
  updateSystemHealthUI();
});
