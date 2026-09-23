import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.schemas import ChecklistCompleteRequest
from app.services import context, rules
from app.services.simulation import simulation

router = APIRouter(prefix="/api/v1/safety", tags=["safety"])


@router.get("/live")
def safety_live(operator_id: str = context.DEFAULT_OPERATOR_ID, persist: bool = True,
                db: Session = Depends(get_db)):
    """Current safety picture: live telemetry + every rule that is firing right now."""
    if context.get_operator(db, operator_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown operator {operator_id}")

    alerts = rules.evaluate(db, operator_id)
    if persist:
        rules.record_alerts(db, operator_id, alerts)

    return {
        "operator_id": operator_id,
        "generated_at": dt.datetime.now(),
        "live": simulation.machine_state(operator_id),
        "hazards": simulation.hazards_for(operator_id),
        "alerts": alerts,
        "counts": {
            "critical": sum(1 for a in alerts if a["severity"] == "Critical"),
            "warning": sum(1 for a in alerts if a["severity"] == "Warning"),
            "caution": sum(1 for a in alerts if a["severity"] == "Caution"),
            "informational": sum(1 for a in alerts if a["severity"] == "Informational"),
        },
    }


@router.get("/events")
def safety_events(operator_id: str = context.DEFAULT_OPERATOR_ID, days: int = 7, limit: int = 100,
                  db: Session = Depends(get_db)):
    since = dt.datetime.now() - dt.timedelta(days=days)
    rows = list(db.scalars(
        select(m.SafetyEvent)
        .where(m.SafetyEvent.operator_id == operator_id, m.SafetyEvent.triggered_at >= since)
        .order_by(m.SafetyEvent.triggered_at.desc())
        .limit(limit)
    ))
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "message": e.message,
            "reason": e.reason,
            "recommended_action": e.recommended_action,
            "source_data": e.source_data,
            "triggered_at": e.triggered_at,
            "resolved_at": e.resolved_at,
            "duration_min": (
                round((e.resolved_at - e.triggered_at).total_seconds() / 60, 1) if e.resolved_at else None
            ),
        }
        for e in rows
    ]


@router.get("/timeline")
def safety_timeline(operator_id: str = context.DEFAULT_OPERATOR_ID, db: Session = Depends(get_db)):
    """Shift-scoped chronological view (PRD §9.4), oldest first, ready to render as a strip."""
    start = context.shift_start()
    rows = list(db.scalars(
        select(m.SafetyEvent)
        .where(m.SafetyEvent.operator_id == operator_id, m.SafetyEvent.triggered_at >= start)
        .order_by(m.SafetyEvent.triggered_at)
    ))
    entries = []
    for e in rows:
        entries.append({"at": e.triggered_at, "kind": "raised", "event_type": e.event_type,
                        "severity": e.severity, "label": e.message})
        if e.resolved_at:
            entries.append({"at": e.resolved_at, "kind": "resolved", "event_type": e.event_type,
                            "severity": "Informational", "label": f"{e.event_type.replace('_', ' ')} resolved"})
    entries.sort(key=lambda x: x["at"])
    return {"shift_start": start, "entries": entries}


@router.get("/checklist")
def get_checklist(task_id: str | None = None, operator_id: str = context.DEFAULT_OPERATOR_ID,
                  db: Session = Depends(get_db)):
    task = db.get(m.Task, task_id) if task_id else (
        context.get_current_task(db, operator_id) or context.get_next_task(db, operator_id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="No task available for a checklist")
    machine = db.get(m.Machine, task.machine_id)
    items = rules.generate_checklist(
        machine.machine_type if machine else None, task.task_type, context.get_latest_environment(db)
    )
    return {
        "task_id": task.id,
        "task_type": task.task_type,
        "machine_type": machine.machine_type if machine else None,
        "items": items,
        "completed": rules.checklist_completed(db, task.operator_id, task.id),
    }


@router.post("/checklists/{task_id}/complete")
def complete_checklist(task_id: str, payload: ChecklistCompleteRequest, db: Session = Depends(get_db)):
    task = db.get(m.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task {task_id}")
    machine = db.get(m.Machine, task.machine_id)
    required = rules.generate_checklist(
        machine.machine_type if machine else None, task.task_type, context.get_latest_environment(db)
    )
    missing = [item for item in required if item not in payload.completed_items]
    if missing:
        raise HTTPException(status_code=400, detail={"message": "Checklist incomplete", "missing": missing})

    now = dt.datetime.now()
    db.add(m.SafetyEvent(
        operator_id=payload.operator_id,
        machine_id=task.machine_id,
        task_session_id=None,
        event_type="checklist_completed",
        severity="Informational",
        message=f"Pre-operation checklist completed for {task.task_type}.",
        reason="Completion is recorded so the pre-task safety gate is auditable.",
        recommended_action="No action required.",
        source_data=f"task_id={task.id}, items={len(payload.completed_items)}",
        triggered_at=now,
        resolved_at=now,
    ))
    db.commit()
    return {"task_id": task.id, "completed": True, "completed_at": now, "items": payload.completed_items}
