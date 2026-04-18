"""
Media playback control service for LadyLinux.

Wraps playerctl, which communicates with MPRIS-compatible media players
(Spotify, VLC, Firefox, Chromium, etc.) over D-Bus. All commands run as
the desktop user via _desktop_runner — D-Bus is not available in the
ladylinux service user context.

Exposed tools: media_play, media_pause, media_toggle, media_next,
               media_prev, media_stop, media_status, media_volume_set,
               media_shuffle_toggle, media_loop_cycle
"""

from __future__ import annotations

from api_layer.services._desktop_runner import run_as_desktop_user


def media_play() -> dict:
    """Resume playback on the active media player."""
    result = run_as_desktop_user(["playerctl", "play"])
    return {
        "ok": result["ok"],
        "message": "Playback started" if result["ok"] else result["stderr"],
    }


def media_pause() -> dict:
    """Pause the active media player."""
    result = run_as_desktop_user(["playerctl", "pause"])
    return {
        "ok": result["ok"],
        "message": "Playback paused" if result["ok"] else result["stderr"],
    }


def media_toggle() -> dict:
    """Toggle play/pause on the active media player."""
    result = run_as_desktop_user(["playerctl", "play-pause"])
    return {
        "ok": result["ok"],
        "message": "Playback toggled" if result["ok"] else result["stderr"],
    }


def media_next() -> dict:
    """Skip to the next track."""
    result = run_as_desktop_user(["playerctl", "next"])
    return {
        "ok": result["ok"],
        "message": "Skipped to next track" if result["ok"] else result["stderr"],
    }


def media_prev() -> dict:
    """Go back to the previous track."""
    result = run_as_desktop_user(["playerctl", "previous"])
    return {
        "ok": result["ok"],
        "message": "Went to previous track" if result["ok"] else result["stderr"],
    }


def media_stop() -> dict:
    """Stop playback entirely."""
    result = run_as_desktop_user(["playerctl", "stop"])
    return {
        "ok": result["ok"],
        "message": "Playback stopped" if result["ok"] else result["stderr"],
    }


def media_status() -> dict:
    """
    Return current playback state and full track metadata.

    Uses one formatted metadata call plus status and position, avoiding the
    older per-field subprocess calls.
    """
    status_result = run_as_desktop_user(["playerctl", "status"])
    if not status_result["ok"]:
        return {
            "ok": True,
            "playing": False,
            "status": "No player",
            "title": "",
            "artist": "",
            "album": "",
            "position_sec": 0.0,
            "duration_sec": 0.0,
            "volume": None,
            "player_name": "",
            "shuffle": False,
            "loop_status": "None",
            "message": "No media player active",
        }

    fmt = "\t".join(
        [
            "{{title}}",
            "{{artist}}",
            "{{album}}",
            "{{mpris:length}}",
            "{{volume}}",
            "{{playerName}}",
            "{{shuffle}}",
            "{{loopStatus}}",
        ]
    )
    meta_result = run_as_desktop_user(["playerctl", "metadata", "--format", fmt])
    position_result = run_as_desktop_user(["playerctl", "position"])

    title = artist = album = player_name = loop_status = ""
    duration_sec = 0.0
    volume: float | None = None
    shuffle = False

    if meta_result["ok"] and meta_result["stdout"]:
        parts = meta_result["stdout"].split("\t")

        def _get(idx: int) -> str:
            return parts[idx].strip() if idx < len(parts) else ""

        title = _get(0)
        artist = _get(1)
        album = _get(2)

        try:
            duration_sec = int(_get(3)) / 1_000_000
        except ValueError:
            duration_sec = 0.0

        try:
            volume = round(float(_get(4)), 2)
        except ValueError:
            volume = None

        player_name = _get(5)
        shuffle = _get(6).lower() == "on"
        loop_status = _get(7) or "None"

    position_sec = 0.0
    if position_result["ok"]:
        try:
            position_sec = float(position_result["stdout"].strip())
        except ValueError:
            pass

    status = status_result["stdout"].strip()
    playing = status.lower() == "playing"

    return {
        "ok": True,
        "playing": playing,
        "status": status,
        "title": title,
        "artist": artist,
        "album": album,
        "position_sec": position_sec,
        "duration_sec": duration_sec,
        "volume": volume,
        "player_name": player_name,
        "shuffle": shuffle,
        "loop_status": loop_status,
        "message": f"{title} - {artist}" if title else status,
    }


def media_volume_set(level: float) -> dict:
    """
    Set playerctl volume.

    level is 0.0-1.0. Clamps to valid range before sending to avoid
    playerctl errors.
    """
    clamped = max(0.0, min(1.0, level))
    result = run_as_desktop_user(["playerctl", "volume", str(round(clamped, 2))])
    return {
        "ok": result["ok"],
        "message": (
            f"Volume set to {int(clamped * 100)}%"
            if result["ok"]
            else result["stderr"]
        ),
    }


def media_shuffle_toggle() -> dict:
    """Toggle playerctl shuffle when supported by the active player."""
    current = run_as_desktop_user(["playerctl", "shuffle"])
    next_state = "Off"
    if current["ok"] and current["stdout"].lower() != "on":
        next_state = "On"

    result = run_as_desktop_user(["playerctl", "shuffle", next_state])
    return {
        "ok": result["ok"],
        "message": f"Shuffle {next_state.lower()}" if result["ok"] else result["stderr"],
    }


def media_loop_cycle() -> dict:
    """Cycle playerctl loop status through None, Track, and Playlist."""
    current = run_as_desktop_user(["playerctl", "loop"])
    states = ["None", "Track", "Playlist"]
    current_state = current["stdout"] if current["ok"] else "None"

    try:
        next_state = states[(states.index(current_state) + 1) % len(states)]
    except ValueError:
        next_state = "None"

    result = run_as_desktop_user(["playerctl", "loop", next_state])
    return {
        "ok": result["ok"],
        "message": f"Repeat {next_state.lower()}" if result["ok"] else result["stderr"],
    }
