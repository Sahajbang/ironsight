from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import context, search as search_service

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search")
def search(q: str, operator_id: str = context.DEFAULT_OPERATOR_ID, limit: int = 12,
           content_type: str | None = None, use_context: bool = True, db: Session = Depends(get_db)):
    """Hybrid search. Context-aware by default: the operator's machine and current task
    re-rank results, so the same query answers differently in different situations (§11.5).
    """
    machine = context.get_machine_for_operator(db, operator_id) if use_context else None
    task = (context.get_current_task(db, operator_id) or context.get_next_task(db, operator_id)) if use_context else None
    operator = context.get_operator(db, operator_id) if use_context else None

    return search_service.grouped_search(
        db, q, limit=limit,
        machine_type=machine.machine_type if machine else None,
        task_type=task.task_type if task else None,
        skill_level=operator.skill_level if operator else None,
        content_type=content_type,
    )


@router.post("/search/reindex")
def reindex(db: Session = Depends(get_db)):
    search_service.index.build(db, force=True)
    return {"reindexed": True, "documents": len(search_service.index._docs)}
