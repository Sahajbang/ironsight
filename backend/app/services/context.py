"""Shared lookups every feature area needs: who is the operator, what are they doing now,
what machine are they on, what is the weather. Kept in one place so routers stay thin.
"""
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m

DEFAULT_OPERATOR_ID = "OP1001"
SHIFT_START_HOUR = 6


def get_operator(db: Session, operator_id: str) -> m.Operator | None:
    return db.get(m.Operator, operator_id)


def list_operators(db: Session) -> list[m.Operator]:
    return list(db.scalars(select(m.Operator).order_by(m.Operator.id)))


def get_machine_for_operator(db: Session, operator_id: str) -> m.Machine | None:
    task = db.scalars(
        select(m.Task).where(m.Task.operator_id == operator_id).order_by(m.Task.planned_start.desc())
    ).first()
    return db.get(m.Machine, task.machine_id) if task else None


def get_today_tasks(db: Session, operator_id: str) -> list[m.Task]:
    return list(
        db.scalars(
            select(m.Task)
            .where(m.Task.operator_id == operator_id, m.Task.shift_date == dt.date.today())
            .order_by(m.Task.planned_start)
        )
    )


def get_current_task(db: Session, operator_id: str) -> m.Task | None:
    return db.scalars(
        select(m.Task).where(
            m.Task.operator_id == operator_id,
            m.Task.shift_date == dt.date.today(),
            m.Task.status == "In Progress",
        )
    ).first()


def get_next_task(db: Session, operator_id: str) -> m.Task | None:
    return db.scalars(
        select(m.Task)
        .where(
            m.Task.operator_id == operator_id,
            m.Task.shift_date == dt.date.today(),
            m.Task.status.in_(["Ready", "Not Started"]),
        )
        .order_by(m.Task.planned_start)
    ).first()


def get_active_session(db: Session, operator_id: str) -> m.TaskSession | None:
    return db.scalars(
        select(m.TaskSession)
        .where(m.TaskSession.operator_id == operator_id, m.TaskSession.ended_at.is_(None))
        .order_by(m.TaskSession.started_at.desc())
    ).first()


def get_session_for_task(db: Session, task_id: str) -> m.TaskSession | None:
    return db.scalars(
        select(m.TaskSession).where(m.TaskSession.task_id == task_id).order_by(m.TaskSession.started_at.desc())
    ).first()


def get_latest_environment(db: Session) -> m.EnvironmentSnapshot | None:
    return db.scalars(
        select(m.EnvironmentSnapshot).order_by(m.EnvironmentSnapshot.timestamp.desc())
    ).first()


def get_recent_sessions(db: Session, operator_id: str, task_type: str | None = None, limit: int = 30) -> list[m.TaskSession]:
    stmt = select(m.TaskSession).where(
        m.TaskSession.operator_id == operator_id, m.TaskSession.actual_time_min.is_not(None)
    )
    if task_type:
        stmt = stmt.where(m.TaskSession.task_type == task_type)
    return list(db.scalars(stmt.order_by(m.TaskSession.started_at.desc()).limit(limit)))


def shift_start(now: dt.datetime | None = None) -> dt.datetime:
    now = now or dt.datetime.now()
    return dt.datetime.combine(now.date(), dt.time(SHIFT_START_HOUR, 0))


def serialize_operator(operator: m.Operator) -> dict:
    return {
        "id": operator.id,
        "name": operator.name,
        "skill_level": operator.skill_level,
        "experience_years": operator.experience_years,
    }


def serialize_machine(machine: m.Machine | None) -> dict | None:
    if machine is None:
        return None
    return {
        "id": machine.id,
        "machine_type": machine.machine_type,
        "model": machine.model,
        "age_years": machine.age_years,
        "engine_hours": machine.engine_hours,
    }


def serialize_environment(env: m.EnvironmentSnapshot | None) -> dict | None:
    if env is None:
        return None
    return {
        "timestamp": env.timestamp,
        "weather": env.weather,
        "temperature_c": env.temperature_c,
        "wind_kph": env.wind_kph,
        "visibility": env.visibility,
        "ground_condition": env.ground_condition,
    }


def serialize_task(task: m.Task, session: m.TaskSession | None = None, eta: dict | None = None) -> dict:
    return {
        "id": task.id,
        "operator_id": task.operator_id,
        "machine_id": task.machine_id,
        "site_id": task.site_id,
        "zone": task.zone,
        "task_type": task.task_type,
        "priority": task.priority,
        "shift_date": task.shift_date,
        "planned_start": task.planned_start,
        "estimated_duration_min": task.estimated_duration_min,
        "ai_predicted_duration_min": task.ai_predicted_duration_min,
        "expected_completion": (
            task.planned_start + dt.timedelta(minutes=task.ai_predicted_duration_min or task.estimated_duration_min)
        ),
        "status": task.status,
        "dependencies": task.dependencies,
        "required_training": task.required_training,
        "safety_requirements": task.safety_requirements,
        "progress_pct": session.progress_pct if session else 0.0,
        "elapsed_min": (
            round((dt.datetime.now() - session.started_at).total_seconds() / 60, 1)
            if session and session.ended_at is None
            else None
        ),
        "eta": eta,
    }


def serialize_session(session: m.TaskSession | None) -> dict | None:
    if session is None:
        return None
    return {
        "id": session.id,
        "task_id": session.task_id,
        "task_type": session.task_type,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "estimated_time_min": session.estimated_time_min,
        "actual_time_min": session.actual_time_min,
        "idle_time_min": session.idle_time_min,
        "load_cycles": session.load_cycles,
        "fuel_used_l": session.fuel_used_l,
        "progress_pct": session.progress_pct,
        "weather": session.weather,
    }
