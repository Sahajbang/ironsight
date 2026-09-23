import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.services import context, eta as eta_service, recommendations, rules
from app.services.simulation import simulation

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(operator_id: str = context.DEFAULT_OPERATOR_ID, db: Session = Depends(get_db)):
    operator = context.get_operator(db, operator_id)
    if operator is None:
        raise HTTPException(status_code=404, detail=f"Unknown operator {operator_id}")

    machine = context.get_machine_for_operator(db, operator_id)
    env = context.get_latest_environment(db)
    tasks = context.get_today_tasks(db, operator_id)
    current_task = context.get_current_task(db, operator_id)
    active_session = context.get_active_session(db, operator_id)
    alerts = rules.evaluate(db, operator_id)
    live = simulation.machine_state(operator_id)
    now = dt.datetime.now()

    task_payload = []
    for task in tasks:
        session = context.get_session_for_task(db, task.id)
        stored = db.scalars(
            select(m.EtaPrediction).where(m.EtaPrediction.task_id == task.id)
            .order_by(m.EtaPrediction.predicted_at.desc())
        ).first()
        eta = None
        if stored is not None:
            eta = {
                "point_estimate_min": stored.point_estimate_min,
                "low_estimate_min": stored.low_estimate_min,
                "high_estimate_min": stored.high_estimate_min,
                "confidence": stored.confidence,
            }
        task_payload.append(context.serialize_task(task, session, eta))

    current_payload = None
    if current_task is not None:
        prediction = eta_service.predict_for_task(db, current_task)
        current_payload = {
            **context.serialize_task(current_task, active_session, prediction),
            "objective": f"{current_task.task_type} in {current_task.zone}",
            "session": context.serialize_session(active_session),
            "relevant_alerts": [a for a in alerts if a["severity"] in ("Critical", "Warning")][:3],
        }

    completed = [t for t in tasks if t.status == "Completed"]
    remaining = [t for t in tasks if t.status != "Completed"]
    today_sessions = [
        s for s in context.get_recent_sessions(db, operator_id, limit=50)
        if s.started_at.date() == dt.date.today()
    ]
    time_on_task = sum(s.actual_time_min or 0 for s in today_sessions)
    idle_time = sum(s.idle_time_min for s in today_sessions)
    incidents_today = db.scalars(
        select(m.Incident).where(m.Incident.operator_id == operator_id,
                                 m.Incident.created_at >= dt.datetime.combine(dt.date.today(), dt.time.min))
    ).all()

    predicted_finish = None
    if remaining:
        total_remaining = sum((t.ai_predicted_duration_min or t.estimated_duration_min) for t in remaining)
        predicted_finish = now + dt.timedelta(minutes=total_remaining)

    return {
        "shift": {
            "operator": context.serialize_operator(operator),
            "machine": context.serialize_machine(machine),
            "site_id": tasks[0].site_id if tasks else "SITE01",
            "shift_date": dt.date.today(),
            "shift_start": context.shift_start(now),
            "current_time": now,
            "connectivity": "Online",
            "machine_status": live.get("operating_state", "Unknown"),
            "environment": context.serialize_environment(env),
        },
        "tasks": task_payload,
        "current_task": current_payload,
        "summary": {
            "tasks_total": len(tasks),
            "tasks_completed": len(completed),
            "tasks_remaining": len(remaining),
            "time_on_task_min": round(time_on_task, 1),
            "idle_time_min": round(idle_time, 1),
            "safety_events": len(alerts),
            "incidents_logged": len(incidents_today),
            "predicted_shift_completion": predicted_finish,
        },
        "safety": {
            "alert_count": len(alerts),
            "highest_severity": alerts[0]["severity"] if alerts else "Normal",
            "alerts": alerts[:4],
            "live": live,
        },
        "next_best_actions": recommendations.next_best_actions(db, operator_id),
    }
