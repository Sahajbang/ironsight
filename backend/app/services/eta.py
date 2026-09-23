"""Task-time prediction (PRD §13).

Returns a *range* with contributing factors, never a bare number. Factor attribution is a
counterfactual pass: re-predict with one feature reset to its typical value and report the
delta in minutes, which is per-prediction (unlike global feature importances) and cheap
enough to run inline.

ponytail: counterfactual deltas instead of the SHAP dependency — same question answered
("why is the ETA longer today?"), one fewer package. Swap in SHAP if interaction effects
start mattering.
"""
import json
import os
from statistics import median

import joblib
from sqlalchemy.orm import Session

from app import models as m
from app.services import context

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "eta_model.joblib")

TASK_TYPES = ["Earth Excavation", "Trenching", "Material Loading", "Grading", "Demolition"]
WEATHERS = ["Sunny", "Cloudy", "Rainy", "Windy"]
SKILL_ORDINAL = {"Beginner": 0.0, "Intermediate": 1.0, "Expert": 2.0}

FEATURE_NAMES = (
    ["estimated_time_min", "machine_age", "skill_ordinal", "hist_median"]
    + [f"task_{t}" for t in TASK_TYPES]
    + [f"weather_{w}" for w in WEATHERS]
)

_cache: dict = {}


def build_row(estimated: float, machine_age: float, skill: str, hist_median: float,
              task_type: str, weather: str) -> list[float]:
    row = [
        float(estimated),
        float(machine_age),
        SKILL_ORDINAL.get(skill, 1.0),
        float(hist_median),
    ]
    row += [1.0 if task_type == t else 0.0 for t in TASK_TYPES]
    row += [1.0 if weather == w else 0.0 for w in WEATHERS]
    return row


def load_model() -> dict | None:
    if "bundle" in _cache:
        return _cache["bundle"]
    if not os.path.exists(MODEL_PATH):
        return None
    bundle = joblib.load(MODEL_PATH)
    _cache["bundle"] = bundle
    return bundle


def _heuristic(estimated: float, task_type: str, weather: str, skill: str) -> float:
    factor = 1.0
    if weather == "Rainy" and task_type in ("Earth Excavation", "Trenching", "Demolition"):
        factor *= 1.15
    if weather == "Windy" and task_type == "Grading":
        factor *= 1.08
    factor *= {"Beginner": 1.20, "Intermediate": 1.05, "Expert": 0.97}.get(skill, 1.0)
    return estimated * factor


def _history(db: Session, operator_id: str | None, task_type: str) -> tuple[float, int]:
    """Median actual duration and sample count for this operator+task type."""
    if operator_id is None:
        return 0.0, 0
    sessions = context.get_recent_sessions(db, operator_id, task_type=task_type, limit=20)
    durations = [s.actual_time_min for s in sessions if s.actual_time_min is not None]
    if not durations:
        return 0.0, 0
    return float(median(durations)), len(durations)


def predict(db: Session, task_type: str, estimated_duration_min: float, weather: str = "Sunny",
            operator_skill: str = "Intermediate", machine_age: float = 3.0,
            operator_id: str | None = None) -> dict:
    hist_median, sample_count = _history(db, operator_id, task_type)
    bundle = load_model()

    if bundle is None:
        point = _heuristic(estimated_duration_min, task_type, weather, operator_skill)
        spread = 0.18
        return {
            "point_estimate_min": round(point, 1),
            "low_estimate_min": round(point * (1 - spread), 1),
            "high_estimate_min": round(point * (1 + spread), 1),
            "confidence": "Low",
            "top_factors": [
                {"name": "Planned duration", "impact_min": round(point - estimated_duration_min, 1),
                 "direction": "increase" if point > estimated_duration_min else "decrease",
                 "detail": "Model not trained yet — using a rule-based estimate."}
            ],
            "baseline_comparison": {"historical_median_min": round(hist_median, 1) if hist_median else None,
                                    "sample_count": sample_count},
            "model": "heuristic",
        }

    model = bundle["model"]
    residual_std = bundle["residual_std"]
    typical = bundle["typical"]
    effective_hist = hist_median or typical["hist_median"]

    row = build_row(estimated_duration_min, machine_age, operator_skill, effective_hist, task_type, weather)
    point = float(model.predict([row])[0])

    # Counterfactual factor attribution: reset one input to "typical", re-predict, take the delta.
    counterfactuals = {
        "Current weather": build_row(estimated_duration_min, machine_age, operator_skill, effective_hist, task_type, "Sunny"),
        "Operator experience": build_row(estimated_duration_min, machine_age, "Intermediate", effective_hist, task_type, weather),
        "Machine age": build_row(estimated_duration_min, typical["machine_age"], operator_skill, effective_hist, task_type, weather),
        "Historical cycle duration": build_row(estimated_duration_min, machine_age, operator_skill, typical["hist_median"], task_type, weather),
        "Planned task size": build_row(typical["estimated_time_min"], machine_age, operator_skill, effective_hist, task_type, weather),
    }
    factors = []
    for name, cf_row in counterfactuals.items():
        delta = point - float(model.predict([cf_row])[0])
        if abs(delta) < 0.5:
            continue
        factors.append({
            "name": name,
            "impact_min": round(delta, 1),
            "direction": "increase" if delta > 0 else "decrease",
            "detail": _factor_detail(name, weather, operator_skill, machine_age, effective_hist),
        })
    factors.sort(key=lambda f: abs(f["impact_min"]), reverse=True)

    confidence = "High" if sample_count >= 5 else ("Medium" if sample_count >= 3 else "Low")
    sigma = {"High": 0.8, "Medium": 1.0, "Low": 1.4}[confidence] * residual_std

    return {
        "point_estimate_min": round(point, 1),
        "low_estimate_min": round(max(point - sigma, point * 0.5), 1),
        "high_estimate_min": round(point + sigma, 1),
        "confidence": confidence,
        "top_factors": factors[:3],
        "baseline_comparison": {
            "historical_median_min": round(hist_median, 1) if hist_median else None,
            "sample_count": sample_count,
            "delta_vs_baseline_min": round(point - hist_median, 1) if hist_median else None,
        },
        "model": "gradient_boosting",
    }


def _factor_detail(name: str, weather: str, skill: str, machine_age: float, hist_median: float) -> str:
    return {
        "Current weather": f"Weather today is {weather}.",
        "Operator experience": f"Operator skill level is {skill}.",
        "Machine age": f"Assigned machine is {machine_age:g} years old.",
        "Historical cycle duration": f"Recent comparable tasks averaged about {hist_median:.0f} min.",
        "Planned task size": "Planned duration differs from a typical task of this type.",
    }.get(name, "")


def predict_for_task(db: Session, task: m.Task) -> dict:
    """Convenience wrapper: predict using everything we know about a stored task."""
    operator = context.get_operator(db, task.operator_id)
    env = context.get_latest_environment(db)
    machine = db.get(m.Machine, task.machine_id)
    return predict(
        db,
        task_type=task.task_type,
        estimated_duration_min=task.estimated_duration_min,
        weather=env.weather if env else "Sunny",
        operator_skill=operator.skill_level if operator else "Intermediate",
        machine_age=machine.age_years if machine else 3.0,
        operator_id=task.operator_id,
    )


def format_range(eta: dict) -> str:
    return f"{eta['low_estimate_min']:.0f}–{eta['high_estimate_min']:.0f} min"


def factors_json(eta: dict) -> str:
    return json.dumps([f["name"] for f in eta.get("top_factors", [])])
