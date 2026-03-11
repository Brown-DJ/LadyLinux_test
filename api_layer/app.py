from __future__ import annotations

from datetime import datetime
import json
import threading
import time
from typing import Any, Literal

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
from api_layer.routes.theme import router as theme_router
from api_layer.routes.ws import router as ws_router
from api_layer.services.system_service import get_status
from api_layer.utils.command_runner import run_command
from api_layer.utils.validators import validate_service_name
from rag_layer.retriever import build_context_block, retrieve
from rag_layer.seed import seed
from rag_layer.vector_store import COLLECTION_NAME, client, ensure_collection
from llm_runtime import ensure_model
from app.response_formatter import format_command_response
from app.shell_router import run_shell_command
from app.tool_router import ToolRouter, ToolRouterError

app = FastAPI()

# Composition root: route groups are modular and independently testable.
app.include_router(system_router)
app.include_router(services_router)
app.include_router(firewall_router)
app.include_router(network_router)
app.include_router(storage_router)
app.include_router(logs_router)
app.include_router(packages_router)
app.include_router(theme_router)
app.include_router(ws_router)

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
- /api/theme/*
- /api/storage/*
- /api/logs/*
- /api/packages/*

RAG context should be used for explanation and project knowledge only.
"""

# tools.json is the single source of truth for allowed tool calls.
# Add new tools there (and implement matching API routes) instead of prompt text.
TOOL_ROUTER = ToolRouter()


class PromptRequest(BaseModel):
    prompt: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _error_payload(
    *,
    error_type: str,
    message: str,
    suggestion: str,
    status_code: int,
    details: Any | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "ok": False,
        "error_type": error_type,
        "message": message,
        "suggestion": suggestion,
    }
    if details is not None:
        payload["details"] = details
    return JSONResponse(content=payload, status_code=status_code)


def classify_prompt(message: str) -> Literal["tool", "rag", "chat"]:
    text = message.lower().strip()

    command_words = (
        "service",
        "restart",
        "firewall",
        "network",
        "status",
        "user",
        "theme",
    )

    knowledge_words = (
        "explain",
        "why",
        "how",
        "architecture",
        "documentation",
        "docs",
    )

    if any(x in text for x in command_words):
        return "tool"

    if any(x in text for x in knowledge_words):
        return "rag"

    return "chat"


def classify_rag_domain(message: str) -> Literal["docs", "code", "system-help"]:
    text = (message or "").strip().lower()

    if any(term in text for term in ("api", "endpoint", "route", "function", "class", "module", "script", "code")):
        return "code"
    if any(term in text for term in ("service", "firewall", "network", "users", "theme", "system", "troubleshoot", "fix")):
        return "system-help"
    return "docs"


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw[start : end + 1]
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("model response did not contain a JSON object")


def _plan_tool_call(prompt: str, context_text: str) -> tuple[str | None, dict[str, Any]]:
    """
    Ask the model to choose from the explicit tool contract only.

    This step blocks hallucinated endpoints/commands by forcing selection from tools.json.
    """
    tools_manifest = json.dumps(TOOL_ROUTER.get_tools_manifest(), indent=2)
    planning_prompt = f"""
You are choosing whether to call a system tool.
Return strict JSON only, no markdown, no prose.

Canonical tool schema (tools.json):
{tools_manifest}

Response schema:
{{
  "tool": "<tool_name_or_null>",
  "parameters": {{}}
}}

User question:
{prompt}

Relevant project context:
{context_text or "No relevant context."}
"""
    selection = _ollama_generate(planning_prompt, model="mistral")
    payload = _extract_json_object(selection)
    tool_name = payload.get("tool")
    parameters = payload.get("parameters", {})
    if tool_name in (None, "", "null"):
        return None, {}
    if not isinstance(tool_name, str):
        raise ValueError("tool must be a string or null")
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")
    return tool_name, parameters


def handle_tool_prompt(prompt: str) -> dict[str, Any]:
    tool_name, tool_parameters = _plan_tool_call(prompt, "")
    if not tool_name:
        raise ToolRouterError("No tool selected for tool-routed request")
    return TOOL_ROUTER.execute(tool_name, tool_parameters)


def handle_rag_prompt(prompt: str) -> tuple[str, list[dict], str]:
    domain = classify_rag_domain(prompt)
    context_results = retrieve(prompt, domain=domain)
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
- Do not invent tools, shell commands, or undocumented endpoints.
"""
    output = _ollama_generate(system_prompt, model="mistral")
    return output, context_results, domain


def handle_hybrid_prompt(prompt: str) -> tuple[str, dict[str, Any] | None, list[dict], str]:
    domain = classify_rag_domain(prompt)
    context_results = retrieve(prompt, domain=domain)
    context_text = build_context_block(context_results)

    tool_name, tool_parameters = _plan_tool_call(prompt, context_text)
    tool_result: dict[str, Any] | None = None
    if tool_name:
        tool_result = TOOL_ROUTER.execute(tool_name, tool_parameters)

    system_prompt = f"""
SYSTEM CAPABILITIES
{CAPABILITY_BLOCK}

RELEVANT PROJECT FILES
{context_text or "No relevant Lady Linux project context was retrieved."}

USER QUESTION
{prompt}

TOOL RESULT
{json.dumps(tool_result, indent=2) if tool_result is not None else "No tool was needed."}

Rules:
- Prefer information found inside RELEVANT PROJECT FILES and TOOL RESULT.
- If not present, respond with "Information not found in system context."
- Do not invent configuration or runtime state.
- Do not invent tools, shell commands, or undocumented endpoints.
"""
    output = _ollama_generate(system_prompt, model="mistral")
    return output, tool_result, context_results, domain


def handle_chat_prompt(prompt: str) -> str:
    chat_prompt = f"""
You are Lady Linux, a Linux assistant. Keep responses concise and accurate.
If a live system action is required, say to use a supported API tool.

User question:
{prompt}
"""
    return _ollama_generate(chat_prompt, model="mistral")


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


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "ok" in detail and "error_type" in detail:
        return JSONResponse(content=detail, status_code=exc.status_code)
    return _error_payload(
        error_type="request_failed",
        message=str(detail),
        suggestion="Check request parameters and endpoint availability.",
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return _error_payload(
        error_type="internal_error",
        message=str(exc),
        suggestion="Retry the request. If it persists, inspect backend logs.",
        status_code=500,
    )


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
    # Pipeline architecture:
    # 1) shell router (command parser + direct tool execution) fast path
    # 2) RAG for documentation/explanations
    # 3) LLM chat fallback
    prompt = req.prompt
    shell_result = run_shell_command(prompt)

    # COMMAND EXECUTION
    if isinstance(shell_result, dict) and shell_result.get("type") == "command":
        formatted_answer = format_command_response(shell_result["tool"], shell_result["result"])
        return JSONResponse(
            content={
                "answer": formatted_answer,
                "response": formatted_answer,
                "route": "command",
                "tool": shell_result["tool"],
                "tool_result": shell_result["result"],
            }
        )

    if isinstance(shell_result, dict) and shell_result.get("type") == "error":
        return JSONResponse(
            content={
                "answer": f"Command failed: {shell_result['error']}",
                "route": "error",
            }
        )

    route = classify_prompt(prompt)

    try:
        # After shell command handling, non-command prompts follow the
        # documentation/explanation path or conversational fallback.
        if route in ("rag", "tool"):
            output, context_results, domain = handle_rag_prompt(prompt)
            return JSONResponse(
                content={
                    "answer": output,
                    "response": output,
                    "model": "mistral",
                    "route": route,
                    "rag_domain": domain,
                    "retrieved_chunks": len(context_results),
                    "tool_result": None,
                }
            )
        if route == "chat":
            output = handle_chat_prompt(prompt)
            return JSONResponse(
                content={
                    "answer": output,
                    "response": output,
                    "model": "mistral",
                    "route": route,
                    "retrieved_chunks": 0,
                    "tool_result": None,
                }
            )
        return _error_payload(
            error_type="route_resolution_failed",
            message="Prompt route could not be resolved.",
            suggestion="Use a clearer request or verify classify_prompt routing.",
            status_code=400,
        )
    except ToolRouterError as exc:
        return _error_payload(
            error_type="tool_execution_failed",
            message=str(exc),
            suggestion="Add missing endpoint to API and tools.json or adjust tool parameters.",
            status_code=400,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        return _error_payload(
            error_type="invalid_tool_payload",
            message=str(exc),
            suggestion="Ensure tool planner returns valid JSON with allowed parameters.",
            status_code=400,
        )
    except requests.RequestException as exc:
        return _error_payload(
            error_type="llm_backend_unavailable",
            message=f"LLM request failed: {exc}",
            suggestion="Verify Ollama runtime availability at http://127.0.0.1:11434.",
            status_code=502,
        )


@app.post("/ask")
async def ask(req: PromptRequest):
    """
    Unified chat endpoint that shares the hybrid shell pipeline with /ask_rag:
    command shell first, then RAG/LLM fallback.
    """
    shell_result = run_shell_command(req.prompt)

    if isinstance(shell_result, dict) and shell_result.get("type") == "command":
        formatted_answer = format_command_response(shell_result["tool"], shell_result["result"])
        return {
            "answer": formatted_answer,
            "response": formatted_answer,
            "route": "command",
            "tool": shell_result["tool"],
            "tool_result": shell_result["result"],
        }

    if isinstance(shell_result, dict) and shell_result.get("type") == "error":
        return {
            "answer": f"Command failed: {shell_result['error']}",
            "route": "error",
        }

    route = classify_prompt(req.prompt)
    if route == "rag":
        output, context_results, domain = handle_rag_prompt(req.prompt)
        return {
            "type": "rag",
            "response": output,
            "model": "mistral",
            "rag_domain": domain,
            "retrieved_chunks": len(context_results),
        }
    output = handle_chat_prompt(req.prompt)
    return {"type": "llm", "response": output, "model": "mistral"}


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
