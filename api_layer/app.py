from datetime import datetime

import json
import requests
import threading
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from api_layer import os_core
from api_layer.command_security import run_whitelisted
from api_layer.firewall_core import get_firewall_status_json
from api_layer.system_services import router as system_router
from api_layer.system_status import (
    get_active_sessions,
    get_active_users,
    get_cpu_load,
    get_disk_usage,
    get_firewall_status,
    get_linux_users,
    get_memory_usage,
    get_system_status,
    get_system_arch,
)
from rag_layer.retriever import build_context_block, retrieve
from rag_layer.seed import seed
from rag_layer.vector_store import COLLECTION_NAME, client, ensure_collection

app = FastAPI()

# Register system service management routes under /api/system/* so the
# System -> Services tab can call deterministic backend endpoints.
app.include_router(system_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

LOG_FILE = "/var/log/ladylinux/actions.log"

OLLAMA_URL = "http://localhost:11434/api/generate"

CAPABILITY_BLOCK = """
You are Lady Linux, an AI system controller.

You run inside the Lady Linux operating environment.

System capabilities include:

• View system metrics
• Manage Linux users
• Manage firewall rules using UFW
• Change Lady Linux UI themes
• Read system configuration files

Available APIs:

/api/system/status
/api/system/users
/api/system/sessions
/api/firewall/status
/api/firewall/allow
/api/firewall/remove

When the user asks for an action that matches these capabilities,
you should perform the action using system APIs rather than explaining Linux commands.
"""


def _load_theme_keys():
    try:
        with open("static/themes.json", "r", encoding="utf-8") as handle:
            theme_data = json.load(handle)
        themes = theme_data.get("themes", {})
        if isinstance(themes, dict):
            return list(themes.keys())
    except Exception:
        pass
    return ["soft", "crimson", "glass", "terminal", "custom-1", "custom-2", "custom-3", "custom-4"]


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/firewall")
def firewall_page(request: Request):
    return templates.TemplateResponse("firewall.html", {"request": request})


@app.post("/users")
@app.get("/users")
def users_page(request: Request):
    return templates.TemplateResponse("users.html", {"request": request})


@app.post("/os")
@app.get("/os")
def os_page(request: Request):
    return templates.TemplateResponse("os.html", {"request": request})


class PromptRequest(BaseModel):
    prompt: str


class FirewallAllowRequest(BaseModel):
    port: int


class FirewallRemoveRequest(BaseModel):
    rule_number: int


def _ollama_generate(prompt: str, model: str = "mistral:latest") -> str:
    response = requests.post(
        OLLAMA_URL,
        json={"model": model, "prompt": prompt}
    )
    response.raise_for_status()

    output = ""
    for line in response.text.strip().splitlines():
        try:
            chunk = json.loads(line)
            output += chunk.get("response", "")
        except json.JSONDecodeError:
            output += line
    return output


def _format_context(results: list[dict]) -> str:
    if not results:
        return "No relevant system context was retrieved."

    sections = []
    for item in results:
        source = item.get("source_path", "unknown")
        domain = item.get("domain", "general")
        line_start = item.get("line_start", 0)
        line_end = item.get("line_end", 0)
        text = item.get("text", "")
        sections.append(
            f"[Source: {source} | Domain: {domain} | Lines: {line_start}-{line_end}]\n{text}"
        )
    return "\n\n".join(sections)


def rag_collection_is_empty():
    """
    Determine whether the vector collection already contains data.

    If the collection has zero stored points, it means the system has not
    completed ingestion and we must run seed().

    If points already exist, we skip reseeding to avoid re-embedding the same
    system files every time the API starts.
    """
    try:
        info = client().get_collection(COLLECTION_NAME)
        points_count = getattr(info, "points_count", None)
        # Treat unknown/None counts as empty to keep startup safe.
        return not points_count or points_count == 0
    except Exception as e:
        print("RAG collection check failed:", e)
        return True


@app.on_event("startup")
def init_rag():
    """
    Initialize the RAG system on API startup.

    Ensures the vector collection exists and conditionally runs ingestion
    only when the collection is empty.
    """
    ensure_collection()

    if rag_collection_is_empty():
        print("RAG collection empty - starting initial seed process")
        # Run ingestion in background thread so API starts immediately.
        threading.Thread(target=seed, daemon=True).start()
    else:
        print("RAG collection already populated - skipping seed")


@app.post("/ask_phi3")
async def ask_phi3_post(req: PromptRequest):
    ui_prompt_prefix = (
        "You are the Lady Linux assistant.\n\n"
        "RULES:\n"
        "1. Reply normally in natural language.\n"
        "2. If and only if the user explicitly requests a UI, theme, color, typography, spacing, density, motion, or visual appearance change, you MUST append exactly one final line.\n"
        "3. That final line MUST follow this exact format:\n"
        'LL_UI: {"action":"update_profile","profile":{...}}\n'
        "4. The LL_UI line must:\n"
        "- Be valid JSON.\n"
        "- Not be wrapped in quotes.\n"
        "- Not be inside markdown.\n"
        "- Not be explained.\n"
        "- Contain only allowed keys.\n"
        "- Be the final line of the response.\n\n"
        "ALLOWED PROFILE FIELDS:\n"
        "- palette.bg_main\n"
        "- palette.accent_primary\n"
        "- palette.text_mode\n"
        "- typography.font_family\n"
        "- typography.base_size\n"
        "- typography.scale\n"
        "- shape.radius\n"
        "- shape.density\n"
        "- effects.shadow_strength\n"
        "- effects.motion_speed\n"
        "- effects.glow_intensity\n\n"
        "If no UI change is requested, do NOT output LL_UI.\n\n"
        f"User request:\n{req.prompt}"
    )

    def stream():
        resp = requests.post(
            OLLAMA_URL,
            json={"model": "mistral:latest", "prompt": ui_prompt_prefix},
            stream=True
        )
        for line in resp.iter_lines():
            if line:
                chunk = json.loads(line)
                yield chunk.get("response", "")

    return StreamingResponse(stream(), media_type="text/plain")


@app.get("/ask_phi3")
def ask_phi3_get(prompt: str):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral:latest", "prompt": prompt}
    )
    return {"output": response.text}


@app.post("/ask_rag")
async def ask_rag(req: PromptRequest):
    prompt = req.prompt
    context_results = retrieve(prompt)
    # Inject live runtime telemetry on every query so the model can ground
    # answers/actions in the machine's current state instead of stale guesses.
    runtime_state = get_system_status()

    # Build structured RAG evidence with file metadata headers for better
    # grounding and easier debugging of retrieved project context.
    context_text = build_context_block(context_results)

    # ------------------------------------------------------------
    # RAG SYSTEM PROMPT
    # This ensures the LLM uses system data instead of hallucinating
    # ------------------------------------------------------------
    system_prompt = f"""
SYSTEM CAPABILITIES
{CAPABILITY_BLOCK}

SYSTEM STATE
{json.dumps(runtime_state, indent=2)}

RELEVANT PROJECT FILES
{context_text or "No relevant Lady Linux project context was retrieved."}

USER QUESTION
{prompt}

Rules:
- Prefer information found inside RELEVANT PROJECT FILES.
- If the answer is not present there, respond with "Information not found in system context."
- Do not invent system configuration.
- Keep answers clear and concise.
"""

    try:
        # ------------------------------------------------------------
        # DEV DEBUG: show retrieved context in server logs
        # This helps developers verify RAG retrieval quality
        # ------------------------------------------------------------
        print("------ RAG CONTEXT START ------")
        print(context_text[:2000])
        print("------ RAG CONTEXT END ------")

        output = _ollama_generate(system_prompt, model="mistral")
        # Return response metadata so frontend Dev Mode can display diagnostics.
        return JSONResponse(content={
            # "answer" is kept for lightweight status polling helpers.
            "answer": output,
            # "response" is kept for existing chat transports.
            "response": output,
            "model": "mistral",
            "retrieved_chunks": len(context_results),
        })
    except Exception as e:
        return JSONResponse(content={
            "answer": f"Lady Linux: Error - {str(e)}",
            "response": f"Lady Linux: Error - {str(e)}",
        }, status_code=500)


@app.post("/ask_firewall")
async def ask_firewall(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")

    fw_json = get_firewall_status_json()

    full_prompt = f"""
User question: {prompt}

Firewall status (JSON structure below for reference):
{json.dumps(fw_json, indent=2)}

Explain this firewall configuration clearly for a Linux user.
"""

    try:
        output = _ollama_generate(full_prompt)
        return PlainTextResponse(content=f"Lady Linux: {output.strip()}")

    except Exception as e:
        return PlainTextResponse(content=f"Lady Linux: Error - {str(e)}")


def log_action(action, target, status):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps({
            "time": datetime.now().isoformat(),
            "action": action,
            "target": target,
            "status": status
        }) + "\n")


@app.post("/disable_service")
def disable_service(target: str):
    try:
        run_whitelisted(["systemctl", "disable", target], check=True)
        run_whitelisted(["systemctl", "stop", target], check=True)
        log_action("disable_service", target, "success")
        return {"status": "ok", "message": f"{target} disabled on boot."}
    except Exception as e:
        log_action("disable_service", target, "failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system")
def api_system():
    return os_core.handle_intent({
        "intent": "system.snapshot",
        "args": {},
        "meta": {"dry_run": False},
    })


@app.get("/api/system/status")
def system_status():
    """
    Return live system telemetry metrics using psutil.

    Each metric maps directly to runtime host state so the dashboard and LLM
    can reason about current CPU, memory, disk, and uptime values.
    """
    metrics = get_system_status()
    return {
        # Current CPU utilization percentage.
        "cpu": metrics.get("cpu"),
        # RAM usage bytes and total bytes.
        "memory_used": metrics.get("memory_used"),
        "memory_total": metrics.get("memory_total"),
        # Disk free bytes and total bytes on root filesystem.
        "disk_free": metrics.get("disk_free"),
        "disk_total": metrics.get("disk_total"),
        # API process uptime in seconds.
        "uptime": metrics.get("uptime"),
        # Backward-compatible keys used by existing frontend components.
        "cpu_load": get_cpu_load(),
        "memory_usage": get_memory_usage(),
        "disk_usage": get_disk_usage(),
        "active_users": get_active_users(),
        "firewall": get_firewall_status(),
        "arch": get_system_arch(),
    }


@app.get("/api/system/users")
def system_users():
    """
    Return real Linux users from /etc/passwd.

    UID >= 1000 filtering keeps output focused on regular interactive users,
    excluding most system/service accounts.
    """
    return get_linux_users()


@app.get("/api/system/sessions")
def system_sessions():
    """
    Return active login sessions from `who`.
    """
    sessions = get_active_sessions()
    raw_text = "\n".join(
        f"{s.get('user', '')} {s.get('tty', '')} {s.get('date', '')} {s.get('time', '')} ({s.get('host', '')})".strip()
        for s in sessions
    )
    return {"sessions": raw_text, "records": sessions}

@app.get("/api/firewall")
def api_firewall():
    return os_core.handle_intent({
        "intent": "firewall.status",
        "args": {},
        "meta": {"dry_run": False},
    })


@app.get("/api/firewall/status")
def firewall_status():
    """
    Return UFW rules with numbering enabled.

    `status numbered` includes stable rule indices, which are required for
    safe targeted deletion in the remove endpoint.
    """
    result = run_whitelisted(
        ["ufw", "status", "numbered"],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "rules": result.stdout,
        "returncode": result.returncode,
        "stderr": result.stderr,
    }


@app.post("/api/firewall/allow")
def firewall_allow(payload: FirewallAllowRequest):
    """
    Allow a firewall port rule via UFW.
    """
    port = payload.port
    result = run_whitelisted(
        ["ufw", "allow", str(port)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=(result.stderr or result.stdout or "ufw allow failed"))
    return {
        "status": "allowed",
        "port": port,
        "output": result.stdout.strip(),
    }


@app.post("/api/firewall/remove")
def firewall_remove(payload: FirewallRemoveRequest):
    """
    Remove a numbered firewall rule via UFW.
    """
    rule_number = payload.rule_number
    result = run_whitelisted(
        ["ufw", "--force", "delete", str(rule_number)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=(result.stderr or result.stdout or "ufw delete failed"))
    return {
        "status": "deleted",
        "rule_number": rule_number,
        "output": result.stdout.strip(),
    }

@app.get("/api/users")
def api_users():
    return os_core.handle_intent({
        "intent": "users.list",
        "args": {},
        "meta": {"dry_run": False},
    })

@app.post("/api/service/{service}/{action}")
def api_service(service: str, action: str):
    return os_core.handle_intent({
        "intent": "service.action",
        "args": {"name": service, "action": action},
        "meta": {"dry_run": False},
    })


@app.post("/api/intent")
async def api_intent(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="request body must be a JSON object")
    return os_core.handle_intent(payload)
