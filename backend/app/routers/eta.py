from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.schemas import EtaPredictRequest
from app.services import eta as eta_service

router = APIRouter(prefix="/api/v1/eta", tags=["eta"])


@router.post("/predict")
def predict(payload: EtaPredictRequest, db: Session = Depends(get_db)):
    """What-if estimator: returns a range, a confidence and the factors behind it (PRD §13.4)."""
    return eta_service.predict(
        db,
        task_type=payload.task_type,
        estimated_duration_min=payload.estimated_duration_min,
        weather=payload.weather,
        operator_skill=payload.operator_skill,
        machine_age=payload.machine_age,
        operator_id=payload.operator_id,
    )


@router.get("/model")
def model_info():
    bundle = eta_service.load_model()
    if bundle is None:
        return {"trained": False, "model": "heuristic",
                "hint": "Run `python -m app.ml.train_eta` after seeding to train the model."}
    return {
        "trained": True,
        "model": "gradient_boosting",
        "features": bundle["feature_names"],
        "metrics": bundle["metrics"],
        "residual_std": round(bundle["residual_std"], 2),
    }


@router.get("/accuracy")
def accuracy(limit: int = 50, db: Session = Depends(get_db)):
    """Predicted vs actual across completed tasks — the continuous-improvement loop (§13.5)."""
    rows = list(db.scalars(select(m.EtaOutcome).order_by(m.EtaOutcome.recorded_at.desc()).limit(limit)))
    entries = []
    for outcome in rows:
        prediction = db.get(m.EtaPrediction, outcome.eta_prediction_id)
        if prediction is None:
            continue
        entries.append({
            "task_id": prediction.task_id,
            "predicted_min": prediction.point_estimate_min,
            "range": [prediction.low_estimate_min, prediction.high_estimate_min],
            "actual_min": outcome.actual_duration_min,
            "error_min": outcome.error_min,
            "within_range": prediction.low_estimate_min <= outcome.actual_duration_min <= prediction.high_estimate_min,
            "recorded_at": outcome.recorded_at,
        })

    errors = [abs(e["error_min"]) for e in entries]
    covered = [e for e in entries if e["within_range"]]
    return {
        "scored": len(entries),
        "mae_min": round(sum(errors) / len(errors), 2) if errors else None,
        "rmse_min": round((sum(e ** 2 for e in errors) / len(errors)) ** 0.5, 2) if errors else None,
        "interval_coverage": round(len(covered) / len(entries), 3) if entries else None,
        "entries": entries,
    }


@router.get("/tasks/{task_id}")
def task_eta(task_id: str, db: Session = Depends(get_db)):
    task = db.get(m.Task, task_id)
    if task is None:
        return {"task_id": task_id, "error": "unknown task"}
    return {"task_id": task_id, **eta_service.predict_for_task(db, task)}
