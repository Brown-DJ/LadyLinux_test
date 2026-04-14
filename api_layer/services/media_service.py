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
    Return current playback state + extended metadata.

    Added fields vs. original:
      - position_sec  : current playback position in seconds (float)
      - duration_sec  : total track duration in seconds (float)
      - volume        : player volume 0.0-1.0 (float)
      - player_name   : active MPRIS player identity (e.g. 'spotify', 'vlc')
      - shuffle       : shuffle state bool (if supported by player)
      - loop_status   : 'None' | 'Track' | 'Playlist'

    playerctl returns seconds for position and microseconds for length.
    Returns ok=True even with no player; numeric fields default to 0/None.
    """
    # Core transport fields
    status_result = run_as_desktop_user(["playerctl", "status"])
    title_result = run_as_desktop_user(["playerctl", "metadata", "title"])
    artist_result = run_as_desktop_user(["playerctl", "metadata", "artist"])
    album_result = run_as_desktop_user(["playerctl", "metadata", "album"])

    # Extended metadata fields fail silently; not all players expose these.
    position_result = run_as_desktop_user(["playerctl", "position"])
    length_result = run_as_desktop_user(["playerctl", "metadata", "mpris:length"])
    volume_result = run_as_desktop_user(["playerctl", "volume"])
    player_result = run_as_desktop_user(
        ["playerctl", "metadata", "--format", "{{playerName}}"]
    )
    shuffle_result = run_as_desktop_user(["playerctl", "shuffle"])
    loop_result = run_as_desktop_user(["playerctl", "loop"])

    no_player = not status_result["ok"]

    position_sec: float = 0.0
    if position_result["ok"]:
        try:
            position_sec = float(position_result["stdout"])
        except ValueError:
            pass

    duration_sec: float = 0.0
    if length_result["ok"]:
        try:
            duration_sec = int(length_result["stdout"]) / 1_000_000
        except ValueError:
            pass

    volume: float | None = None
    if volume_result["ok"]:
        try:
            volume = round(float(volume_result["stdout"]), 2)
        except ValueError:
            pass

    return {
        "ok": True,  # "no player" is valid state, not an error
        "playing": status_result["stdout"].lower() == "playing" if status_result["ok"] else False,
        "status": status_result["stdout"] if status_result["ok"] else "No player",
        "title": title_result["stdout"] if title_result["ok"] else "",
        "artist": artist_result["stdout"] if artist_result["ok"] else "",
        "album": album_result["stdout"] if album_result["ok"] else "",
        "position_sec": position_sec,
        "duration_sec": duration_sec,
        "volume": volume,
        "player_name": player_result["stdout"] if player_result["ok"] else "",
        "shuffle": shuffle_result["stdout"].lower() == "on" if shuffle_result["ok"] else False,
        "loop_status": loop_result["stdout"] if loop_result["ok"] else "None",
        "message": status_result["stdout"] if not no_player else "No media player active",
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
