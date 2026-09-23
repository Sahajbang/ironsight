import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.schemas import BookingCreate
from app.services import context, recommendations, search

router = APIRouter(prefix="/api/v1", tags=["training"])


def _serialize_content(c: m.TrainingContent, record: m.TrainingRecord | None = None) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "content_type": c.content_type,
        "machine_family": c.machine_family,
        "task_type": c.task_type,
        "skill_level": c.skill_level,
        "duration_min": c.duration_min,
        "body_text": c.body_text,
        "url": c.url,
        "status": record.status if record else "Not Started",
        "score": record.score if record else None,
        "completed_at": record.completed_at if record else None,
    }


@router.get("/training")
def list_training(operator_id: str = context.DEFAULT_OPERATOR_ID, content_type: str | None = None,
                  machine_family: str | None = None, task_type: str | None = None,
                  db: Session = Depends(get_db)):
    stmt = select(m.TrainingContent)
    if content_type:
        stmt = stmt.where(m.TrainingContent.content_type == content_type)
    if machine_family:
        stmt = stmt.where(m.TrainingContent.machine_family.in_([machine_family, "All"]))
    if task_type:
        stmt = stmt.where(m.TrainingContent.task_type == task_type)
    rows = list(db.scalars(stmt.order_by(m.TrainingContent.content_type, m.TrainingContent.title)))

    records = {
        r.training_content_id: r
        for r in db.scalars(select(m.TrainingRecord).where(m.TrainingRecord.operator_id == operator_id))
    }
    items = [_serialize_content(c, records.get(c.id)) for c in rows]
    categories: dict[str, list[dict]] = {}
    for item in items:
        categories.setdefault(item["content_type"], []).append(item)

    return {
        "total": len(items),
        "items": items,
        "categories": [{"content_type": k, "items": v} for k, v in categories.items()],
        "progress": {
            "completed": sum(1 for i in items if i["status"] == "Completed"),
            "in_progress": sum(1 for i in items if i["status"] == "In Progress"),
            "not_started": sum(1 for i in items if i["status"] == "Not Started"),
        },
    }


@router.get("/training/recommendations")
def training_recommendations(operator_id: str = context.DEFAULT_OPERATOR_ID, limit: int = 4,
                             db: Session = Depends(get_db)):
    if context.get_operator(db, operator_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown operator {operator_id}")
    return recommendations.training_recommendations(db, operator_id, limit=limit)


@router.get("/training/search")
def training_search(q: str, operator_id: str = context.DEFAULT_OPERATOR_ID, limit: int = 10,
                    db: Session = Depends(get_db)):
    machine = context.get_machine_for_operator(db, operator_id)
    task = context.get_current_task(db, operator_id) or context.get_next_task(db, operator_id)
    return search.grouped_search(
        db, q, limit=limit,
        machine_type=machine.machine_type if machine else None,
        task_type=task.task_type if task else None,
    )


@router.get("/training/{content_id}")
def get_training(content_id: str, operator_id: str = context.DEFAULT_OPERATOR_ID, db: Session = Depends(get_db)):
    content = db.get(m.TrainingContent, content_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Unknown training content {content_id}")
    record = db.scalars(
        select(m.TrainingRecord).where(
            m.TrainingRecord.operator_id == operator_id, m.TrainingRecord.training_content_id == content_id
        )
    ).first()
    return _serialize_content(content, record)


@router.post("/training/{content_id}/complete")
def complete_training(content_id: str, payload: BookingCreate, db: Session = Depends(get_db)):
    content = db.get(m.TrainingContent, content_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Unknown training content {content_id}")
    record = db.scalars(
        select(m.TrainingRecord).where(
            m.TrainingRecord.operator_id == payload.operator_id,
            m.TrainingRecord.training_content_id == content_id,
        )
    ).first()
    if record is None:
        record = m.TrainingRecord(operator_id=payload.operator_id, training_content_id=content_id)
        db.add(record)
    record.status = "Completed"
    record.completed_at = dt.datetime.now()
    record.score = record.score or 100.0
    db.commit()
    db.refresh(record)
    return _serialize_content(content, record)


@router.get("/instructors/availability")
def instructor_availability(expertise: str | None = None, db: Session = Depends(get_db)):
    stmt = select(m.InstructorSlot).where(m.InstructorSlot.start_time >= dt.datetime.now())
    if expertise:
        stmt = stmt.where(m.InstructorSlot.expertise == expertise)
    rows = list(db.scalars(stmt.order_by(m.InstructorSlot.start_time)))
    return [
        {
            "id": s.id,
            "instructor_name": s.instructor_name,
            "expertise": s.expertise,
            "topic": s.topic,
            "mode": s.mode,
            "location": s.location,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "booked": s.booked_by_operator_id is not None,
            "booked_by_operator_id": s.booked_by_operator_id,
        }
        for s in rows
    ]


@router.post("/training/bookings/{slot_id}")
def book_slot(slot_id: int, payload: BookingCreate, db: Session = Depends(get_db)):
    slot = db.get(m.InstructorSlot, slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail=f"Unknown slot {slot_id}")
    if slot.booked_by_operator_id is not None:
        raise HTTPException(status_code=409, detail="Slot already booked")
    slot.booked_by_operator_id = payload.operator_id
    db.commit()
    db.refresh(slot)
    return {
        "id": slot.id,
        "instructor_name": slot.instructor_name,
        "topic": slot.topic,
        "mode": slot.mode,
        "location": slot.location,
        "start_time": slot.start_time,
        "end_time": slot.end_time,
        "booked_by_operator_id": slot.booked_by_operator_id,
        "confirmation": f"Booked with {slot.instructor_name} on {slot.start_time:%a %d %b at %H:%M}.",
    }
