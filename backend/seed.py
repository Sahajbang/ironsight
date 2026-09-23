"""Recreate app.db from scratch and load the synthetic dataset. Idempotent: run anytime."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from data_gen.generate import generate
from app.db import Base, SessionLocal, engine
from app import models as m

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    Base.metadata.create_all(bind=engine)

    data = generate()
    db = SessionLocal()
    try:
        for row in data["operators"]:
            db.add(m.Operator(id=row["id"], name=row["name"], skill_level=row["skill_level"], experience_years=row["experience_years"]))
        for row in data["machines"]:
            db.add(m.Machine(**row))
        db.flush()

        for row in data["tasks"]:
            db.add(m.Task(**row))
        db.flush()

        for row in data["task_sessions"]:
            db.add(m.TaskSession(**row))
        db.flush()

        for row in data["operation_events"]:
            db.add(m.OperationEvent(**row))

        for row in data["safety_events"]:
            db.add(m.SafetyEvent(**row))

        for row in data["environment_snapshots"]:
            db.add(m.EnvironmentSnapshot(**row))

        for row in data["training_content"]:
            db.add(m.TrainingContent(**row))
        db.flush()

        for row in data["training_records"]:
            db.add(m.TrainingRecord(**row))

        for row in data["instructor_slots"]:
            db.add(m.InstructorSlot(**row))

        for row in data["incidents"]:
            db.add(m.Incident(**row))

        for row in data["anomaly_events"]:
            db.add(m.AnomalyEvent(**row))

        pred_objs = []
        for row in data["eta_predictions"]:
            obj = m.EtaPrediction(**row)
            db.add(obj)
            pred_objs.append(obj)
        db.flush()  # populate autoincrement ids on pred_objs before outcomes reference them

        for row in data["eta_outcomes"]:
            row = dict(row)
            idx = row.pop("_prediction_index")
            db.add(m.EtaOutcome(eta_prediction_id=pred_objs[idx].id, **row))

        db.commit()
        print(
            f"Seeded: {len(data['operators'])} operators, {len(data['machines'])} machines, "
            f"{len(data['tasks'])} tasks, {len(data['task_sessions'])} task_sessions, "
            f"{len(data['operation_events'])} operation_events, {len(data['safety_events'])} safety_events, "
            f"{len(data['environment_snapshots'])} environment_snapshots, "
            f"{len(data['training_content'])} training_content, {len(data['training_records'])} training_records, "
            f"{len(data['instructor_slots'])} instructor_slots, {len(data['incidents'])} incidents, "
            f"{len(data['anomaly_events'])} anomaly_events, {len(data['eta_predictions'])} eta_predictions, "
            f"{len(data['eta_outcomes'])} eta_outcomes."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
