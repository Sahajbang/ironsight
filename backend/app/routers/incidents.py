import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.schemas import IncidentCreate, IncidentStatusUpdate
from app.services import context
from app.services.simulation import simulation

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])

STATUS_FLOW = ["Reported", "Acknowledged", "Under Investigation", "Resolved"]


def _serialize(incident: m.Incident) -> dict:
    return {
        "id": incident.id,
        "operator_id": incident.operator_id,
        "machine_id": incident.machine_id,
        "task_id": incident.task_id,
        "category": incident.category,
        "severity": incident.severity,
        "description": incident.description,
        "location": incident.location,
        "status": incident.status,
        "photo_url": incident.photo_url,
        "created_at": incident.created_at,
        "updated_at": incident.updated_at,
        "next_status": (
            STATUS_FLOW[STATUS_FLOW.index(incident.status) + 1]
            if incident.status in STATUS_FLOW and incident.status != "Resolved" else None
        ),
    }


@router.get("")
def list_incidents(operator_id: str | None = None, status: str | None = None, limit: int = 50,
                   db: Session = Depends(get_db)):
    stmt = select(m.Incident)
    if operator_id:
        stmt = stmt.where(m.Incident.operator_id == operator_id)
    if status:
        stmt = stmt.where(m.Incident.status == status)
    rows = list(db.scalars(stmt.order_by(m.Incident.created_at.desc()).limit(limit)))
    return [_serialize(r) for r in rows]


@router.post("", status_code=201)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    """One-tap incident creation — machine/task context is attached automatically (PRD §9.1-C)."""
    if context.get_operator(db, payload.operator_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown operator {payload.operator_id}")

    machine_id = payload.machine_id
    task_id = payload.task_id
    if machine_id is None or task_id is None:
        task = context.get_current_task(db, payload.operator_id) or context.get_next_task(db, payload.operator_id)
        machine = context.get_machine_for_operator(db, payload.operator_id)
        machine_id = machine_id or (machine.id if machine else None)
        task_id = task_id or (task.id if task else None)

    now = dt.datetime.now()
    incident = m.Incident(
        operator_id=payload.operator_id,
        machine_id=machine_id,
        task_id=task_id,
        category=payload.category,
        severity=payload.severity,
        description=payload.description,
        location=payload.location,
        status="Reported",
        photo_url=payload.photo_url,
        created_at=now,
        updated_at=now,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    state = simulation.operator_state(payload.operator_id)
    if state:
        state["operating_state"] = "Incident"
        simulation.emit(payload.operator_id, "incident_reported",
                        f"Incident reported: {payload.category} in {payload.location}.")

    return _serialize(incident)


@router.get("/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.get(m.Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Unknown incident {incident_id}")
    return _serialize(incident)


@router.patch("/{incident_id}/status")
def update_status(incident_id: int, payload: IncidentStatusUpdate, db: Session = Depends(get_db)):
    incident = db.get(m.Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Unknown incident {incident_id}")
    incident.status = payload.status
    incident.updated_at = dt.datetime.now()
    db.commit()
    db.refresh(incident)
    return _serialize(incident)
