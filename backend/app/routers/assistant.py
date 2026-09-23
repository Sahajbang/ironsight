from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import NVIDIA_API_KEY, NVIDIA_MODEL
from app.db import get_db
from app.schemas import AssistantMessageRequest
from app.services import assistant as assistant_service, guide_registry

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


@router.post("/message")
def message(payload: AssistantMessageRequest, db: Session = Depends(get_db)):
    """Chat turn. Returns the reply plus a validated UI guide plan for the pointer to run."""
    return assistant_service.chat(
        db,
        message=payload.message,
        operator_id=payload.operator_id,
        route=payload.route,
        task_id=payload.task_id,
    )


@router.post("/guide")
def guide(target: str, message: str | None = None):
    """Ask for a guide plan directly, without going through the LLM."""
    return assistant_service.guide(target, message)


@router.get("/guide/targets")
def guide_targets():
    return {
        "targets": guide_registry.list_targets(),
        "workflows": guide_registry.list_workflows(),
        "allowed_actions": sorted(guide_registry.ALLOWED_ACTIONS),
        "restricted_actions": sorted(guide_registry.RESTRICTED_ACTIONS),
    }


@router.post("/guide/walkthrough")
def walkthrough(workflow: str):
    """Run a named multi-step walkthrough without going through the LLM."""
    actions = guide_registry.plan_for_workflow(workflow)
    if not actions:
        return {"workflow": workflow, "actions": [], "error": "unknown workflow"}
    return {"workflow": workflow, "actions": actions, "steps": sum(1 for a in actions if a["waitForUser"])}


@router.get("/status")
def status():
    return {
        "llm_configured": bool(NVIDIA_API_KEY),
        "model": NVIDIA_MODEL if NVIDIA_API_KEY else None,
        "provider": "nvidia-nemotron",
        "fallback": "deterministic keyword router over the same tools",
    }
