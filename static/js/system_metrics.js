async function updateSystemMetrics() {
  try {
    const response = await fetch("/api/system/status");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    const cpu = Number(data.cpu ?? data.cpu_load ?? 0);
    const memoryUsed = Number(data.memory_used ?? 0);
    const memoryTotal = Number(data.memory_total ?? 0);
    const diskFree = Number(data.disk_free ?? 0);
    const diskTotal = Number(data.disk_total ?? 0);

    const cpuValue = document.getElementById("cpu_value");
    const memoryValue = document.getElementById("memory_value");
    const diskValue = document.getElementById("disk_value");

    if (cpuValue) {
      cpuValue.textContent = `${cpu.toFixed(1)}% CPU usage`;
    }

    if (memoryValue) {
      const memPercent = memoryTotal > 0 ? (memoryUsed / memoryTotal) * 100 : 0;
      memoryValue.textContent = `${memPercent.toFixed(1)}% RAM used`;
    }

    if (diskValue) {
      const diskUsed = diskTotal - diskFree;
      const diskPercent = diskTotal > 0 ? (diskUsed / diskTotal) * 100 : 0;
      diskValue.textContent = `${diskPercent.toFixed(1)}% disk used`;
    }
  } catch (err) {
    console.error("System metrics update failed:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  updateSystemMetrics();
});

setInterval(updateSystemMetrics, 3000);
