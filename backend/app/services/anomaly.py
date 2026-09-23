"""Operator Behavior Fingerprint + explainable anomaly detection (PRD §12).

The question is never "is this value high?" but "is this high *for this operator, on this
machine, doing this task, under these conditions?*" — so every baseline is scoped to
(operator, task_type) and every detection carries the comparison that produced it.

Two layers, both explainable:
  1. robust z-score (median/MAD) per behavioral dimension — says which dimension deviated
  2. IsolationForest across the dimensions together — catches combinations that look normal
     one-at-a-time but odd jointly; used as supporting evidence, never on its own
"""
import datetime as dt
from statistics import median

import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.services import context

Z_THRESHOLD = 3.5
RATIO_THRESHOLD = 1.5
MIN_HISTORY = 3
MIN_FOREST_SAMPLES = 8

CONTEXT_LABELS = {
    "truck_wait": "Truck availability delay recorded during this task.",
    "excessive_idle": "Extended idle period with no recorded dependency.",
}


def _robust_z(value: float, samples: list[float]) -> tuple[float, float]:
    """Return (z, baseline_median). MAD-based so a couple of outliers can't hide a third."""
    med = float(median(samples))
    deviations = [abs(s - med) for s in samples]
    mad = float(median(deviations))
    if mad == 0:
        spread = float(np.std(samples)) or 1e-6
        return 0.6745 * (value - med) / spread, med
    return 0.6745 * (value - med) / mad, med


def _dimensions(session: m.TaskSession) -> dict[str, float]:
    duration = session.actual_time_min or session.estimated_time_min or 1.0
    cycles = max(session.load_cycles, 1)
    return {
        "idle_time": session.idle_time_min,
        "idle_ratio": session.idle_time_min / duration if duration else 0.0,
        "duration_ratio": duration / session.estimated_time_min if session.estimated_time_min else 1.0,
        "fuel_per_cycle": session.fuel_used_l / cycles,
    }


def baselines(db: Session, operator_id: str, task_type: str) -> dict:
    history = context.get_recent_sessions(db, operator_id, task_type=task_type, limit=20)
    if len(history) < MIN_HISTORY:
        return {"sample_count": len(history), "dimensions": {}}
    per_dim: dict[str, list[float]] = {}
    for s in history:
        for name, value in _dimensions(s).items():
            per_dim.setdefault(name, []).append(value)
    return {
        "sample_count": len(history),
        "dimensions": {
            name: {"median": round(float(median(vals)), 3), "min": round(min(vals), 3), "max": round(max(vals), 3)}
            for name, vals in per_dim.items()
        },
    }


def _forest_flag(history: list[m.TaskSession], target: m.TaskSession) -> bool:
    if len(history) < MIN_FOREST_SAMPLES:
        return False
    keys = ["idle_ratio", "duration_ratio", "fuel_per_cycle"]
    X = np.array([[_dimensions(s)[k] for k in keys] for s in history], dtype=float)
    forest = IsolationForest(random_state=42, contamination="auto").fit(X)
    point = np.array([[_dimensions(target)[k] for k in keys]], dtype=float)
    return bool(forest.predict(point)[0] == -1)


def evaluate_session(db: Session, session: m.TaskSession) -> list[dict]:
    """Produce explainable anomaly cards for one session (PRD §12.4)."""
    history = [
        s for s in context.get_recent_sessions(db, session.operator_id, task_type=session.task_type, limit=20)
        if s.id != session.id and s.started_at < session.started_at
    ]
    if len(history) < MIN_HISTORY:
        return []

    current = _dimensions(session)
    forest_flag = _forest_flag(history, session)
    cards: list[dict] = []

    for name in ("idle_time", "duration_ratio", "fuel_per_cycle"):
        samples = [_dimensions(s)[name] for s in history]
        value = current[name]
        z, baseline = _robust_z(value, samples)
        ratio = value / baseline if baseline else 0.0
        if not (z > Z_THRESHOLD or ratio >= RATIO_THRESHOLD) or value <= baseline:
            continue

        week_ago = session.started_at - dt.timedelta(days=7)
        week_samples = [_dimensions(s)[name] for s in history if s.started_at >= week_ago]
        week_median = float(median(week_samples)) if week_samples else baseline

        ctx = session.scenario_profile if session.scenario_profile in CONTEXT_LABELS else None
        cards.append({
            "task_session_id": session.id,
            "operator_id": session.operator_id,
            "task_type": session.task_type,
            "dimension": name,
            "actual_value": round(value, 2),
            "baseline_value": round(baseline, 2),
            "typical_range": [round(min(samples), 2), round(max(samples), 2)],
            "seven_day_median": round(week_median, 2),
            "deviation_score": round(ratio, 2),
            "robust_z": round(z, 2),
            "multivariate_outlier": forest_flag,
            "explanation": _explain(name, session.task_type, value, baseline, ratio),
            "possible_context": CONTEXT_LABELS.get(ctx or "", None),
            "impact_estimate": _impact(name, session, value, baseline, history),
            "detected_at": session.ended_at or dt.datetime.now(),
        })

    return cards


def _explain(dimension: str, task_type: str, value: float, baseline: float, ratio: float) -> str:
    if dimension == "idle_time":
        return (f"Idle time is {ratio:.1f}× your normal {task_type.lower()} baseline "
                f"({value:.0f} min vs {baseline:.0f} min typical).")
    if dimension == "duration_ratio":
        return (f"This {task_type.lower()} task ran {ratio:.1f}× longer relative to its plan than your "
                f"usual ({value:.2f}× planned vs {baseline:.2f}× typical).")
    return (f"Fuel per load cycle is {ratio:.1f}× your {task_type.lower()} baseline "
            f"({value:.2f} L/cycle vs {baseline:.2f} L/cycle typical).")


def _impact(dimension: str, session: m.TaskSession, value: float, baseline: float,
            history: list[m.TaskSession]) -> dict:
    extra = value - baseline
    if dimension == "idle_time":
        rates = [s.fuel_used_l / s.actual_time_min for s in history if s.actual_time_min]
        fuel_rate = float(median(rates)) if rates else 0.1
        return {"added_duration_min": round(extra, 1), "added_fuel_l": round(extra * fuel_rate, 1)}
    if dimension == "duration_ratio":
        return {"added_duration_min": round(extra * (session.estimated_time_min or 0), 1), "added_fuel_l": None}
    return {"added_duration_min": None, "added_fuel_l": round(extra * max(session.load_cycles, 1), 1)}


def detect_for_operator(db: Session, operator_id: str, limit: int = 5, persist: bool = True) -> list[dict]:
    """Scan the operator's recent completed sessions and return (optionally store) new cards."""
    sessions = context.get_recent_sessions(db, operator_id, limit=limit)
    existing = {
        (row.task_session_id, row.dimension)
        for row in db.scalars(select(m.AnomalyEvent).where(m.AnomalyEvent.operator_id == operator_id))
    }
    fresh: list[dict] = []
    for session in sessions:
        for card in evaluate_session(db, session):
            if (card["task_session_id"], card["dimension"]) in existing:
                continue
            fresh.append(card)
            if persist:
                db.add(m.AnomalyEvent(
                    task_session_id=card["task_session_id"],
                    operator_id=card["operator_id"],
                    dimension=card["dimension"],
                    baseline_value=card["baseline_value"],
                    actual_value=card["actual_value"],
                    deviation_score=card["deviation_score"],
                    explanation=card["explanation"],
                    possible_context=card["possible_context"],
                    status="Detected",
                    created_at=card["detected_at"],
                ))
    if persist and fresh:
        db.commit()
    return fresh


def serialize(db: Session, row: m.AnomalyEvent) -> dict:
    session = db.get(m.TaskSession, row.task_session_id)
    return {
        "id": row.id,
        "task_session_id": row.task_session_id,
        "operator_id": row.operator_id,
        "task_id": session.task_id if session else None,
        "task_type": session.task_type if session else None,
        "dimension": row.dimension,
        "baseline_value": row.baseline_value,
        "actual_value": row.actual_value,
        "deviation_score": row.deviation_score,
        "explanation": row.explanation,
        "possible_context": row.possible_context,
        "status": row.status,
        "feedback_reason": row.feedback_reason,
        "created_at": row.created_at,
        "actions": ["view_timeline", "confirm_normal", "report_reason", "get_recommendation"],
    }


def record_feedback(db: Session, anomaly_id: int, status: str, reason: str | None) -> m.AnomalyEvent | None:
    row = db.get(m.AnomalyEvent, anomaly_id)
    if row is None:
        return None
    row.status = status
    row.feedback_reason = reason
    db.commit()
    db.refresh(row)
    return row
