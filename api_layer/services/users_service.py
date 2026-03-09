from __future__ import annotations


def list_users() -> dict:
    users: list[str] = []
    try:
        with open("/etc/passwd", "r", encoding="utf-8") as handle:
            for line in handle:
                entry = line.strip()
                if not entry or entry.startswith("#"):
                    continue
                users.append(entry.split(":", 1)[0])
        return {"ok": True, "users": users, "count": len(users)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "users": [], "count": 0, "stderr": str(exc)}


def get_user(name: str) -> dict:
    target = str(name).strip()
    if not target:
        return {"ok": False, "user": None, "stderr": "Invalid user name"}

    try:
        with open("/etc/passwd", "r", encoding="utf-8") as handle:
            for line in handle:
                entry = line.strip()
                if not entry or entry.startswith("#"):
                    continue
                parts = entry.split(":")
                if len(parts) < 7:
                    continue
                if parts[0] == target:
                    return {
                        "ok": True,
                        "user": {
                            "name": parts[0],
                            "uid": parts[2],
                            "gid": parts[3],
                            "comment": parts[4],
                            "home": parts[5],
                            "shell": parts[6],
                        },
                    }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "user": None, "stderr": str(exc)}

    return {"ok": False, "user": None, "stderr": f"User '{target}' not found"}


def refresh_user(name: str) -> dict:
    detail = get_user(name)
    if not detail.get("ok"):
        return {"ok": False, "refreshed": False, "stderr": detail.get("stderr", "User lookup failed")}
    return {"ok": True, "refreshed": True, "user": detail["user"]}
