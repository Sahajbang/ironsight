import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.schemas import AnomalyFeedback
from app.services import anomaly, context, recommendations

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


@router.get("/anomalies")
def list_anomalies(operator_id: str | None = None, status: str | None = None, detect: bool = True,
                   limit: int = 25, db: Session = Depends(get_db)):
    if detect and operator_id:
        anomaly.detect_for_operator(db, operator_id, limit=5)

    stmt = select(m.AnomalyEvent)
    if operator_id:
        stmt = stmt.where(m.AnomalyEvent.operator_id == operator_id)
    if status:
        stmt = stmt.where(m.AnomalyEvent.status == status)
    rows = list(db.scalars(stmt.order_by(m.AnomalyEvent.created_at.desc()).limit(limit)))
    return [anomaly.serialize(db, row) for row in rows]


@router.get("/anomalies/{anomaly_id}")
def get_anomaly(anomaly_id: int, db: Session = Depends(get_db)):
    row = db.get(m.AnomalyEvent, anomaly_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Unknown anomaly {anomaly_id}")

    payload = anomaly.serialize(db, row)
    session = db.get(m.TaskSession, row.task_session_id)
    if session is not None:
        payload["session"] = context.serialize_session(session)
        payload["baselines"] = anomaly.baselines(db, row.operator_id, session.task_type)
        payload["timeline"] = [
            {"at": e.timestamp, "event_type": e.event_type, "value": e.value, "detail": e.event_metadata}
            for e in db.scalars(
                select(m.OperationEvent).where(m.OperationEvent.task_session_id == session.id)
                .order_by(m.OperationEvent.timestamp)
            )
        ]
        payload["recommendations"] = recommendations.training_recommendations(db, row.operator_id, limit=2)
    return payload


@router.post("/anomalies/{anomaly_id}/feedback")
def anomaly_feedback(anomaly_id: int, payload: AnomalyFeedback, db: Session = Depends(get_db)):
    """The learning loop (PRD §12.5): the operator explains, the system stores the context."""
    row = anomaly.record_feedback(db, anomaly_id, payload.status, payload.reason)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Unknown anomaly {anomaly_id}")
    return anomaly.serialize(db, row)


@router.get("/baselines")
def get_baselines(operator_id: str, task_type: str, db: Session = Depends(get_db)):
    if context.get_operator(db, operator_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown operator {operator_id}")
    return {
        "operator_id": operator_id,
        "task_type": task_type,
        **anomaly.baselines(db, operator_id, task_type),
    }


@router.get("/performance")
def performance(operator_id: str = context.DEFAULT_OPERATOR_ID, days: int = 14, db: Session = Depends(get_db)):
    """Operator/machine insight rollup: utilisation, idle share and ETA accuracy over time."""
    since = dt.datetime.now() - dt.timedelta(days=days)
    sessions = [s for s in context.get_recent_sessions(db, operator_id, limit=200) if s.started_at >= since]
    outcomes = list(db.scalars(
        select(m.EtaOutcome).join(m.EtaPrediction, m.EtaOutcome.eta_prediction_id == m.EtaPrediction.id)
        .join(m.Task, m.EtaPrediction.task_id == m.Task.id)
        .where(m.Task.operator_id == operator_id)
    ))

    total_time = sum(s.actual_time_min or 0 for s in sessions)
    total_idle = sum(s.idle_time_min for s in sessions)
    errors = [abs(o.error_min) for o in outcomes]

    return {
        "operator_id": operator_id,
        "window_days": days,
        "sessions": len(sessions),
        "total_time_min": round(total_time, 1),
        "idle_time_min": round(total_idle, 1),
        "idle_share": round(total_idle / total_time, 3) if total_time else None,
        "load_cycles": sum(s.load_cycles for s in sessions),
        "fuel_used_l": round(sum(s.fuel_used_l for s in sessions), 1),
        "eta_accuracy": {
            "predictions_scored": len(errors),
            "mae_min": round(sum(errors) / len(errors), 2) if errors else None,
        },
        "by_task_type": [
            {
                "task_type": task_type,
                "sessions": len(group),
                "median_duration_min": round(sum(s.actual_time_min or 0 for s in group) / len(group), 1),
                "median_idle_min": round(sum(s.idle_time_min for s in group) / len(group), 1),
            }
            for task_type, group in _group_by_task_type(sessions).items()
        ],
    }


def _group_by_task_type(sessions: list[m.TaskSession]) -> dict[str, list[m.TaskSession]]:
    grouped: dict[str, list[m.TaskSession]] = {}
    for s in sessions:
        grouped.setdefault(s.task_type, []).append(s)
    return grouped
