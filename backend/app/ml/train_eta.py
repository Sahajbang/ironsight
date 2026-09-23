"""Train the task-duration model from seeded task_sessions.

Run after seeding:  python -m app.ml.train_eta
Writes backend/models/eta_model.joblib, which app/services/eta.py loads lazily.

The `hist_median` feature is computed from *prior* sessions only (expanding median), so the
model never sees the session it is predicting — otherwise the historical feature leaks the
target and the reported accuracy is meaningless.
"""
import os
from statistics import median

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sqlalchemy import select

from app import models as m
from app.db import SessionLocal
from app.services.eta import FEATURE_NAMES, MODEL_PATH, build_row


def load_training_rows() -> tuple[np.ndarray, np.ndarray, dict]:
    db = SessionLocal()
    try:
        sessions = list(db.scalars(
            select(m.TaskSession)
            .where(m.TaskSession.actual_time_min.is_not(None))
            .order_by(m.TaskSession.started_at)
        ))
        machines = {mac.id: mac for mac in db.scalars(select(m.Machine))}
    finally:
        db.close()

    if not sessions:
        raise SystemExit("No completed task_sessions found. Run `python seed.py` first.")

    seen: dict[tuple[str, str], list[float]] = {}
    rows, targets = [], []
    for s in sessions:
        key = (s.operator_id, s.task_type)
        prior = seen.get(key, [])
        hist_median = float(median(prior)) if prior else 0.0
        machine = machines.get(s.machine_id)
        rows.append(build_row(
            estimated=s.estimated_time_min,
            machine_age=machine.age_years if machine else s.machine_age,
            skill=s.operator_skill,
            hist_median=hist_median,
            task_type=s.task_type,
            weather=s.weather,
        ))
        targets.append(s.actual_time_min)
        seen.setdefault(key, []).append(s.actual_time_min)

    typical = {
        "estimated_time_min": float(median([s.estimated_time_min for s in sessions])),
        "machine_age": float(median([s.machine_age for s in sessions])),
        "hist_median": float(median([t for t in targets])),
    }
    return np.array(rows, dtype=float), np.array(targets, dtype=float), typical


def main() -> None:
    X, y, typical = load_training_rows()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

    model = GradientBoostingRegressor(n_estimators=250, max_depth=3, learning_rate=0.05, random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    residual_std = float(np.std(y_test - preds))

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({
        "model": model,
        "feature_names": FEATURE_NAMES,
        "residual_std": residual_std,
        "typical": typical,
        "metrics": {"mae": float(mae), "rmse": rmse, "n_train": len(X_train), "n_test": len(X_test)},
    }, MODEL_PATH)

    print(f"Trained on {len(X_train)} sessions, tested on {len(X_test)}.")
    print(f"MAE {mae:.2f} min | RMSE {rmse:.2f} min | residual std {residual_std:.2f} min")
    print(f"Saved -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
