// Dashboard now-playing widget for Spotify.
// Polls /api/spotify/now-playing and updates controls in place.

(function initMusicWidget() {
  const POLL_MS = 10000;

  const elIdle = document.getElementById("musicIdle");
  const elActive = document.getElementById("musicActive");
  const elError = document.getElementById("musicError");
  const elErrorMsg = document.getElementById("musicErrorMsg");
  const elArt = document.getElementById("musicArt");
  const elTitle = document.getElementById("musicTitle");
  const elArtist = document.getElementById("musicArtist");
  const elDevice = document.getElementById("musicDevice");
  const elPlayPauseBtn = document.getElementById("musicPlayPauseBtn");
  const elPlayPauseIcon = document.getElementById("musicPlayPauseIcon");
  const elPrevBtn = document.getElementById("musicPrevBtn");
  const elNextBtn = document.getElementById("musicNextBtn");
  const elBgBlur = document.getElementById("musicBgBlur");
  const elBgToggleBtn = document.getElementById("musicBgToggleBtn");

  if (!elIdle) return;

  let isPlaying = false;
  let currentArt = "";
  let bgActive = false;

  async function fetchNowPlaying() {
    try {
      const response = await fetch("/api/spotify/now-playing");
      const data = await response.json();

      if (!data.ok) {
        showError(data.message || "Spotify unavailable");
        return;
      }

      if (!data.playing && !data.title) {
        showIdle();
        return;
      }

      currentArt = data.art_large || data.art_medium || "";
      showTrack(data);
    } catch (err) {
      console.warn("[music-widget] fetch failed:", err);
      showError("Could not reach Spotify");
    }
  }

  function showIdle() {
    elIdle.classList.remove("d-none");
    elActive.classList.add("d-none");
    elError.classList.add("d-none");
  }

  function showError(message) {
    elIdle.classList.add("d-none");
    elActive.classList.add("d-none");
    elError.classList.remove("d-none");
    elErrorMsg.textContent = message;
  }

  function showTrack(data) {
    elIdle.classList.add("d-none");
    elError.classList.add("d-none");
    elActive.classList.remove("d-none");

    elTitle.textContent = data.title || "Unknown track";
    elArtist.textContent = data.artist || "Unknown artist";
    elDevice.textContent = data.device_name ? `on ${data.device_name}` : "";

    const artUrl = data.art_medium || data.art_thumb || "";
    if (artUrl) {
      elArt.src = artUrl;
      elArt.style.display = "";
    } else {
      elArt.style.display = "none";
    }

    isPlaying = Boolean(data.playing);
    syncPlayPauseIcon();
  }

  function syncPlayPauseIcon() {
    elPlayPauseIcon.className = isPlaying
      ? "bi bi-pause-fill"
      : "bi bi-play-fill";
  }

  async function playerAction(endpoint) {
    try {
      await fetch(`/api/spotify/${endpoint}`, { method: "POST" });
      setTimeout(fetchNowPlaying, 500);
    } catch (err) {
      console.warn("[music-widget] control failed:", endpoint, err);
    }
  }

  if (elBgToggleBtn && elBgBlur) {
    elBgToggleBtn.addEventListener("click", () => {
      if (!bgActive && currentArt) {
        elBgBlur.style.backgroundImage = `url("${currentArt}")`;
        elBgBlur.style.opacity = "1";
        bgActive = true;
        elBgToggleBtn.classList.add("active");
      } else if (bgActive) {
        elBgBlur.style.opacity = "0";
        bgActive = false;
        elBgToggleBtn.classList.remove("active");
      }
    });
  }

  elPrevBtn?.addEventListener("click", () => playerAction("previous"));

  elPlayPauseBtn?.addEventListener("click", () => {
    isPlaying = !isPlaying;
    syncPlayPauseIcon();
    playerAction(isPlaying ? "play" : "pause");
  });

  elNextBtn?.addEventListener("click", () => playerAction("next"));

  fetchNowPlaying();
  setInterval(fetchNowPlaying, POLL_MS);
})();
