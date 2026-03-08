from __future__ import annotations

from datetime import datetime
import json
import threading
import time

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from api_layer import os_core
from api_layer.firewall_core import get_firewall_status_json
from api_layer.routes.firewall import router as firewall_router
from api_layer.routes.logs import router as logs_router
from api_layer.routes.network import router as network_router
from api_layer.routes.packages import router as packages_router
from api_layer.routes.services import router as services_router
from api_layer.routes.storage import router as storage_router
from api_layer.routes.system import router as system_router
from api_layer.services.system_service import get_status
from api_layer.utils.command_runner import run_command
from api_layer.utils.validators import validate_service_name
from rag_layer.retriever import build_context_block, retrieve
from rag_layer.seed import seed
from rag_layer.vector_store import COLLECTION_NAME, client, ensure_collection
from llm_runtime import ensure_model

app = FastAPI()

# Composition root: route groups are modular and independently testable.
app.include_router(system_router)
app.include_router(services_router)
app.include_router(firewall_router)
app.include_router(network_router)
app.include_router(storage_router)
app.include_router(logs_router)
app.include_router(packages_router)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

LOG_FILE = "/var/log/ladylinux/actions.log"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

CAPABILITY_BLOCK = """
You are Lady Linux, an AI system assistant.

Use system API tools/endpoints for live state and actions. Do not generate shell commands.

Primary endpoint groups:
- /api/system/*
- /api/firewall/*
- /api/network/*
- /api/storage/*
- /api/logs/*
- /api/packages/*

RAG context should be used for explanation and project knowledge only.
"""


class PromptRequest(BaseModel):
    prompt: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _ollama_generate(prompt: str, model: str = "mistral") -> str:
    """Call Ollama through its HTTP API and normalize output text."""
    ensure_model()
    response = requests.post(
        OLLAMA_URL,
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()

    # Prefer JSON payload for stream=false responses.
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return str(payload.get("response", ""))
    except Exception:
        pass

    # Fallback for legacy newline-delimited behavior.
    output = ""
    for line in response.text.strip().splitlines():
        try:
            chunk = json.loads(line)
            output += chunk.get("response", "")
        except json.JSONDecodeError:
            output += line
    return output


def rag_collection_is_empty() -> bool:
    """Check whether Qdrant already contains vectors for startup seeding."""
    try:
        info = client().get_collection(COLLECTION_NAME)
        points_count = getattr(info, "points_count", None)
        return not points_count or points_count == 0
    except Exception:
        return True


@app.on_event("startup")
def init_rag() -> None:
    """Create collection and seed only when empty."""
    ensure_collection()
    if rag_collection_is_empty():
        threading.Thread(target=seed, daemon=True).start()

    # Keep startup fast, then opportunistically warm the model later.
    def preload() -> None:
        time.sleep(30)
        ensure_model()

    threading.Thread(target=preload, daemon=True).start()


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


@app.post("/ask_phi3")
async def ask_phi3_post(req: PromptRequest):
    try:
        return PlainTextResponse(content=_ollama_generate(req.prompt, model="mistral"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc


@app.get("/ask_phi3")
def ask_phi3_get(prompt: str):
    try:
        return {"output": _ollama_generate(prompt, model="mistral")}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc


@app.post("/ask_rag")
async def ask_rag(req: PromptRequest):
    """Use RAG for explanations/context only (no live telemetry injection)."""
    prompt = req.prompt
    context_results = retrieve(prompt)
    context_text = build_context_block(context_results)

    system_prompt = f"""
SYSTEM CAPABILITIES
{CAPABILITY_BLOCK}

RELEVANT PROJECT FILES
{context_text or "No relevant Lady Linux project context was retrieved."}

USER QUESTION
{prompt}

Rules:
- Prefer information found inside RELEVANT PROJECT FILES.
- If not present, respond with "Information not found in system context."
- Do not invent configuration or runtime state.
"""

    try:
        output = _ollama_generate(system_prompt, model="mistral")
        return JSONResponse(
            content={
                "answer": output,
                "response": output,
                "model": "mistral",
                "retrieved_chunks": len(context_results),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            content={
                "answer": f"Lady Linux: Error - {str(exc)}",
                "response": f"Lady Linux: Error - {str(exc)}",
            },
            status_code=500,
        )


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    ensure_model()
    response = requests.post(
        "http://127.0.0.1:11434/api/chat",
        json={
            "model": "mistral",
            "messages": [message.model_dump() for message in req.messages],
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


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
        output = _ollama_generate(full_prompt, model="mistral")
        return PlainTextResponse(content=f"Lady Linux: {output.strip()}")
    except Exception as exc:  # noqa: BLE001
        return PlainTextResponse(content=f"Lady Linux: Error - {str(exc)}")


def log_action(action: str, target: str, status: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "time": datetime.now().isoformat(),
                    "action": action,
                    "target": target,
                    "status": status,
                }
            )
            + "\n"
        )


@app.post("/disable_service")
def disable_service(target: str):
    """Compatibility endpoint for existing UI controls."""
    try:
        service_name = validate_service_name(target)
        unit = f"{service_name}.service" if not service_name.endswith(".service") else service_name

        disable_result = run_command(["systemctl", "disable", unit])
        stop_result = run_command(["systemctl", "stop", unit])
        if not disable_result.ok or not stop_result.ok:
            raise HTTPException(
                status_code=500,
                detail={
                    "disable": disable_result.model_dump(),
                    "stop": stop_result.model_dump(),
                },
            )

        log_action("disable_service", service_name, "success")
        return {"status": "ok", "message": f"{service_name} disabled on boot."}
    except ValueError as exc:
        log_action("disable_service", target, "failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Backward-compatible aliases used by legacy frontend paths.
@app.get("/api/system")
def api_system() -> dict:
    return {"ok": True, **get_status()}


@app.get("/api/firewall")
def api_firewall():
    return os_core.handle_intent(
        {
            "intent": "firewall.status",
            "args": {},
            "meta": {"dry_run": False},
        }
    )


@app.get("/api/users")
def api_users():
    return os_core.handle_intent(
        {
            "intent": "users.list",
            "args": {},
            "meta": {"dry_run": False},
        }
    )


@app.post("/api/service/{service}/{action}")
def api_service(service: str, action: str):
    return os_core.handle_intent(
        {
            "intent": "service.action",
            "args": {"name": service, "action": action},
            "meta": {"dry_run": False},
        }
    )


@app.post("/api/intent")
async def api_intent(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="request body must be a JSON object")
    return os_core.handle_intent(payload)
