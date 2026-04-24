"""Friendly application and web service name resolution."""

from __future__ import annotations

from core.tools.desktop_resolver import resolve_desktop_binary


def _normalize_name(name: str) -> str:
    return str(name or "").strip().lower().replace("_", "-").replace(" ", "-")


_APP_REGISTRY = {
    "calculator": {"binary": "gnome-calculator", "process": "gnome-calculator", "type": "desktop"},
    "calendar": {"binary": "gnome-calendar", "process": "gnome-calendar", "type": "desktop"},
    "camera": {"binary": "cheese", "process": "cheese", "type": "desktop"},
    "characters": {"binary": "gnome-characters", "process": "gnome-characters", "type": "desktop"},
    "disks": {"binary": "gnome-disks", "process": "gnome-disks", "type": "desktop"},
    "files": {"binary": "nemo", "process": "nemo", "type": "desktop"},
    "file-manager": {"binary": "nemo", "process": "nemo", "type": "desktop"},
    "firefox": {"binary": "firefox", "process": "firefox", "type": "desktop"},
    "image-viewer": {"binary": "eog", "process": "eog", "type": "desktop"},
    "logs": {"binary": "gnome-logs", "process": "gnome-logs", "type": "desktop"},
    "music": {"binary": "rhythmbox", "process": "rhythmbox", "type": "desktop"},
    "notes": {"binary": "gnote", "process": "gnote", "type": "desktop"},
    "settings": {"binary": "gnome-control-center", "process": "gnome-control-center", "type": "desktop"},
    "software": {"binary": "gnome-software", "process": "gnome-software", "type": "desktop"},
    "spotify": {"binary": "spotify", "process": "spotify", "type": "desktop"},
    "terminal": {"binary": "gnome-terminal", "process": "gnome-terminal", "type": "desktop"},
    "text-editor": {"binary": "gedit", "process": "gedit", "type": "desktop"},
    "videos": {"binary": "totem", "process": "totem", "type": "desktop"},
    "vlc": {"binary": "vlc", "process": "vlc", "type": "desktop"},
}

_ALIASES = {
    "calc": "calculator",
    "gnome-calculator": "calculator",
    "file-browser": "files",
    "file-explorer": "files",
    "nemo": "files",
    "browser": "firefox",
    "web-browser": "firefox",
    "control-center": "settings",
    "system-settings": "settings",
    "shell": "terminal",
    "console": "terminal",
    "gnome-terminal": "terminal",
    "editor": "text-editor",
    "text-editor": "text-editor",
    "gedit": "text-editor",
    "video-player": "videos",
}

# Web-only services (no reliable local binary / should default to browser)
_WEB_SERVICES = {
    # Core / general
    "google", "gmail", "google-docs", "google-drive", "google-sheets",
    "google-slides", "google-photos", "google-calendar",

    # Video / streaming
    "youtube", "netflix", "hulu", "disney-plus", "prime-video",
    "hbo-max", "paramount-plus", "peacock",

    # Social / communities
    "reddit", "twitter", "x", "facebook", "instagram", "tiktok",
    "linkedin", "threads", "snapchat",

    # Dev / technical
    "github", "gitlab", "bitbucket", "stackoverflow",
    "stackexchange", "codepen", "replit",

    # AI / tools
    "chatgpt", "claude", "gemini", "perplexity",
    "midjourney", "runway", "huggingface",

    # Messaging (browser fallback versions)
    "discord", "slack", "messenger", "whatsapp-web",
    "telegram-web",

    # Music (web variants only)
    "spotify-web", "soundcloud", "pandora", "apple-music-web",

    # Shopping / services
    "amazon", "ebay", "etsy", "walmart", "target", "bestbuy",

    # Media / info
    "wikipedia", "imdb", "rottentomatoes",

    # Cloud / storage
    "dropbox", "onedrive", "mega", "icloud",

    # Utilities / tools
    "speedtest", "fast", "canva", "figma",
    "notion", "trello", "asana", "clickup",

    # Finance / misc
    "paypal", "venmo", "cashapp", "stripe-dashboard",

    # Gaming / platforms
    "twitch", "roblox", "steam-store", "epic-games-store",

    # Education
    "coursera", "udemy", "khan-academy", "edx",
}

_WEB_URLS = {
    "apple-music-web": "https://music.apple.com",
    "bestbuy": "https://www.bestbuy.com",
    "cashapp": "https://cash.app",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "codepen": "https://codepen.io",
    "disney-plus": "https://www.disneyplus.com",
    "edx": "https://www.edx.org",
    "epic-games-store": "https://store.epicgames.com",
    "fast": "https://fast.com",
    "gemini": "https://gemini.google.com",
    "google-calendar": "https://calendar.google.com",
    "google-docs": "https://docs.google.com",
    "google-drive": "https://drive.google.com",
    "google-photos": "https://photos.google.com",
    "google-sheets": "https://sheets.google.com",
    "google-slides": "https://slides.google.com",
    "hbo-max": "https://www.max.com",
    "huggingface": "https://huggingface.co",
    "icloud": "https://www.icloud.com",
    "imdb": "https://www.imdb.com",
    "khan-academy": "https://www.khanacademy.org",
    "linkedin": "https://www.linkedin.com",
    "messenger": "https://www.messenger.com",
    "midjourney": "https://www.midjourney.com",
    "onedrive": "https://onedrive.live.com",
    "paramount-plus": "https://www.paramountplus.com",
    "prime-video": "https://www.primevideo.com",
    "rottentomatoes": "https://www.rottentomatoes.com",
    "spotify-web": "https://open.spotify.com",
    "stackexchange": "https://stackexchange.com",
    "stackoverflow": "https://stackoverflow.com",
    "steam-store": "https://store.steampowered.com",
    "stripe-dashboard": "https://dashboard.stripe.com",
    "telegram-web": "https://web.telegram.org",
    "twitter": "https://twitter.com",
    "whatsapp-web": "https://web.whatsapp.com",
    "x": "https://x.com",
}


def resolve_app(name: str) -> dict | None:
    """Return registry metadata for a friendly local app name."""
    normalized = _normalize_name(name)
    key = _ALIASES.get(normalized, normalized)
    return _APP_REGISTRY.get(key)


def get_binary(name: str) -> str | None:
    """
    Resolve a friendly app name to its launch binary.

    Resolution order:
      1. Static `_APP_REGISTRY`
      2. `_ALIASES` to canonical registry names
      3. Dynamic `.desktop` index for installed GUI apps
      4. `None` so downstream code can try raw `shutil.which()`
    """
    normalized = _normalize_name(name)

    if normalized in _APP_REGISTRY:
        return _APP_REGISTRY[normalized]["binary"]

    canonical = _ALIASES.get(normalized)
    if canonical and canonical in _APP_REGISTRY:
        return _APP_REGISTRY[canonical]["binary"]

    return resolve_desktop_binary(normalized)


def get_process_name(name: str) -> str | None:
    app = resolve_app(name)
    return app.get("process") if app else None


def is_web_service(name: str) -> bool:
    return _normalize_name(name) in _WEB_SERVICES


def build_web_url(name: str) -> str:
    normalized = _normalize_name(name)
    if normalized in _WEB_URLS:
        return _WEB_URLS[normalized]
    return f"https://www.{normalized}.com"
