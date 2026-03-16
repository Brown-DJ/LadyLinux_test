import { subscribe } from "./system_metrics.js";

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

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
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

subscribe((data) => {
  if (document.body?.getAttribute("data-page") !== "system") return;
  renderMetrics(data);
});
