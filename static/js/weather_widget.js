// Fetches /api/context/weather and populates the weather tile.
// Polls on a slow interval because the backend owns the heavier caching.

(function initWeatherWidget() {
  const POLL_MS = 5 * 60 * 1000;
  const STALE_THRESHOLD_MS = 15 * 60 * 1000;

  const elTemp = document.getElementById("weatherTemp");
  const elConditions = document.getElementById("weatherConditions");
  const elWind = document.getElementById("weatherWind");
  const elLocation = document.getElementById("weatherLocation");
  const elPeriod = document.getElementById("weatherPeriodName");
  const elNext = document.getElementById("weatherNext");
  const elStale = document.getElementById("weatherStaleWarning");
  const elRefresh = document.getElementById("weatherRefreshBtn");

  if (!elTemp) return;

  async function fetchWeather(forceRefresh = false) {
    try {
      const url = forceRefresh ? "/api/context/weather/refresh" : "/api/context/weather";
      const method = forceRefresh ? "POST" : "GET";
      const response = await fetch(url, { method });
      const payload = await response.json();

      if (!payload.ok || !payload.weather) {
        elConditions.textContent = "Unavailable";
        return;
      }

      render(payload.weather);
    } catch (err) {
      console.warn("[weather] fetch failed:", err);
      elConditions.textContent = "Unavailable";
    }
  }

  function render(weather) {
    elTemp.textContent = weather.temperature_f != null
      ? `${weather.temperature_f}\u00b0${weather.temperature_unit}`
      : "--";
    elConditions.textContent = weather.conditions || "Unknown";
    elWind.textContent = weather.wind_speed && weather.wind_direction
      ? `${weather.wind_speed} ${weather.wind_direction}`
      : weather.wind_speed || "--";
    elLocation.textContent = [weather.city, weather.region].filter(Boolean).join(", ") || "Unknown";
    elPeriod.textContent = weather.period_name || "Next";
    elNext.textContent = weather.next_period || "--";

    const ageMs = weather.fetched_at ? (Date.now() / 1000 - weather.fetched_at) * 1000 : 0;
    elStale.classList.toggle("d-none", ageMs < STALE_THRESHOLD_MS);
  }

  elRefresh?.addEventListener("click", () => {
    elConditions.textContent = "Refreshing...";
    fetchWeather(true);
  });

  fetchWeather();
  setInterval(() => fetchWeather(), POLL_MS);
})();
