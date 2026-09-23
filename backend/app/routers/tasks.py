import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.schemas import TaskCompleteRequest, TaskStatusUpdate
from app.services import anomaly, context, eta as eta_service, rules
from app.services.simulation import simulation

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _stored_eta(db: Session, task_id: str) -> m.EtaPrediction | None:
    return db.scalars(
        select(m.EtaPrediction).where(m.EtaPrediction.task_id == task_id)
        .order_by(m.EtaPrediction.predicted_at.desc())
    ).first()


@router.get("/today")
def tasks_today(operator_id: str = context.DEFAULT_OPERATOR_ID, db: Session = Depends(get_db)):
    tasks = context.get_today_tasks(db, operator_id)
    return [context.serialize_task(t, context.get_session_for_task(db, t.id)) for t in tasks]


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(m.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task {task_id}")
    session = context.get_session_for_task(db, task_id)
    prediction = eta_service.predict_for_task(db, task)
    machine = db.get(m.Machine, task.machine_id)
    return {
        **context.serialize_task(task, session, prediction),
        "machine": context.serialize_machine(machine),
        "session": context.serialize_session(session),
        "checklist": rules.generate_checklist(
            machine.machine_type if machine else None, task.task_type, context.get_latest_environment(db)
        ),
        "checklist_completed": rules.checklist_completed(db, task.operator_id, task_id),
    }


@router.get("/{task_id}/eta")
def task_eta(task_id: str, db: Session = Depends(get_db)):
    task = db.get(m.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task {task_id}")
    return {"task_id": task_id, **eta_service.predict_for_task(db, task)}


@router.post("/{task_id}/start")
def start_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(m.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task {task_id}")
    if task.status == "Completed":
        raise HTTPException(status_code=409, detail="Task is already completed")

    existing = context.get_active_session(db, task.operator_id)
    if existing is not None and existing.task_id != task_id:
        raise HTTPException(status_code=409, detail=f"Task {existing.task_id} is already in progress")

    operator = context.get_operator(db, task.operator_id)
    machine = db.get(m.Machine, task.machine_id)
    env = context.get_latest_environment(db)
    prediction = eta_service.predict_for_task(db, task)

    session = existing or m.TaskSession(
        task_id=task.id,
        operator_id=task.operator_id,
        machine_id=task.machine_id,
        task_type=task.task_type,
        weather=env.weather if env else "Sunny",
        operator_skill=operator.skill_level if operator else "Intermediate",
        machine_age=machine.age_years if machine else 3.0,
        started_at=dt.datetime.now(),
        estimated_time_min=task.estimated_duration_min,
        idle_time_min=0.0,
        load_cycles=0,
        fuel_used_l=0.0,
        progress_pct=0.0,
        scenario_profile="live",
    )
    db.add(session)
    task.status = "In Progress"
    task.ai_predicted_duration_min = prediction["point_estimate_min"]
    db.add(m.EtaPrediction(
        task_id=task.id,
        point_estimate_min=prediction["point_estimate_min"],
        low_estimate_min=prediction["low_estimate_min"],
        high_estimate_min=prediction["high_estimate_min"],
        confidence=prediction["confidence"],
        top_factors=eta_service.factors_json(prediction),
        predicted_at=dt.datetime.now(),
    ))
    db.commit()
    db.refresh(session)

    state = simulation.operator_state(task.operator_id)
    if state:
        state["current_task_id"] = task.id
        state["task_status"] = "In Progress"
        state["operating_state"] = "Active"

    return {"task": context.serialize_task(task, session, prediction), "session_id": session.id, "eta": prediction}


@router.post("/{task_id}/complete")
def complete_task(task_id: str, payload: TaskCompleteRequest, db: Session = Depends(get_db)):
    task = db.get(m.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task {task_id}")
    session = context.get_session_for_task(db, task_id)
    if session is None:
        raise HTTPException(status_code=409, detail="Task has no session to complete — start it first")

    now = dt.datetime.now()
    elapsed = (now - session.started_at).total_seconds() / 60
    session.ended_at = now
    session.actual_time_min = round(payload.actual_time_min or max(elapsed, 1.0), 1)
    if payload.idle_time_min is not None:
        session.idle_time_min = payload.idle_time_min
    session.progress_pct = 100.0
    task.status = "Completed"

    prediction = _stored_eta(db, task_id)
    outcome = None
    if prediction is not None:
        error = round(session.actual_time_min - prediction.point_estimate_min, 1)
        row = m.EtaOutcome(
            eta_prediction_id=prediction.id,
            actual_duration_min=session.actual_time_min,
            error_min=error,
            recorded_at=now,
        )
        db.add(row)
        outcome = {
            "predicted_min": prediction.point_estimate_min,
            "predicted_range": [prediction.low_estimate_min, prediction.high_estimate_min],
            "actual_min": session.actual_time_min,
            "error_min": error,
            "within_range": prediction.low_estimate_min <= session.actual_time_min <= prediction.high_estimate_min,
        }
    db.commit()

    new_anomalies = anomaly.detect_for_operator(db, task.operator_id, limit=3)

    state = simulation.operator_state(task.operator_id)
    if state:
        state["task_status"] = "Completed"
        state["operating_state"] = "Idle"

    return {
        "task": context.serialize_task(task, session),
        "eta_outcome": outcome,
        "new_anomalies": new_anomalies,
    }


@router.patch("/{task_id}/status")
def update_status(task_id: str, payload: TaskStatusUpdate, db: Session = Depends(get_db)):
    task = db.get(m.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task {task_id}")
    task.status = payload.status
    db.commit()
    db.refresh(task)
    return context.serialize_task(task, context.get_session_for_task(db, task_id))
