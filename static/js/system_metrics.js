/*
-------------------------------------------------------
Lady Linux - Shared System Metrics Engine
-------------------------------------------------------

Single polling service used by all UI pages.

Responsibilities:
- Poll backend metrics endpoint
- Cache latest metrics payload
- Emit updates through UI event bus
- Prevent duplicate pollers
*/

import { emit } from "./ui_event_bus.js";

const METRICS_ENDPOINT = "/api/system/status";
const POLL_INTERVAL = 3000;

if (!window.__LL_METRICS_ENGINE) {
  window.__LL_METRICS_ENGINE = {
    running: false,
    cache: null,
    intervalId: null,
  };

  async function pollMetrics() {
    try {
      const response = await fetch(METRICS_ENDPOINT, { cache: "no-store" });
      if (!response.ok) return;

      const data = await response.json();
      window.__LL_METRICS_ENGINE.cache = data;
      emit("metrics:update", data);
    } catch (error) {
      console.warn("Metrics poll failed", error);
    }
  }

  function startEngine() {
    if (window.__LL_METRICS_ENGINE.running) return;

    window.__LL_METRICS_ENGINE.running = true;
    pollMetrics();
    window.__LL_METRICS_ENGINE.intervalId = window.setInterval(pollMetrics, POLL_INTERVAL);
  }

  startEngine();
}

export function getLatestMetrics() {
  return window.__LL_METRICS_ENGINE?.cache ?? null;
}
