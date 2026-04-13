# api_layer/routes/memory_routes.py
# REST endpoints for reading and writing persistent user facts.
# Register in app.py: app.include_router(memory_router)

from fastapi import APIRouter
from pydantic import BaseModel

from core.memory.user_facts import (
    delete_fact,
    load_user_facts,
    upsert_fact,
)

memory_router = APIRouter(prefix="/api/memory", tags=["memory"])


class FactUpsertRequest(BaseModel):
    key: str    # e.g. "name", "preferred_editor", "timezone"
    value: str  # plain string value


class FactDeleteRequest(BaseModel):
    key: str


@memory_router.get("/facts")
def get_facts():
    """Return all stored user facts."""
    return {"ok": True, "data": load_user_facts()}


@memory_router.post("/facts")
def set_fact(req: FactUpsertRequest):
    """Add or update a single user fact."""
    upsert_fact(req.key, req.value)
    return {"ok": True, "message": f"Fact '{req.key}' saved."}


@memory_router.delete("/facts")
def remove_fact(req: FactDeleteRequest):
    """Delete a user fact by key."""
    removed = delete_fact(req.key)
    return {"ok": removed, "message": f"Fact '{req.key}' {'removed' if removed else 'not found'}."}
