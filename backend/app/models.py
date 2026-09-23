import datetime as dt

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    skill_level: Mapped[str] = mapped_column(String)  # Beginner / Intermediate / Expert
    experience_years: Mapped[float] = mapped_column(Float, default=0)


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    machine_type: Mapped[str] = mapped_column(String)  # Excavator / Loader
    model: Mapped[str] = mapped_column(String)
    age_years: Mapped[float] = mapped_column(Float, default=0)
    engine_hours: Mapped[float] = mapped_column(Float, default=0)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"))
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"))
    site_id: Mapped[str] = mapped_column(String, default="SITE01")
    zone: Mapped[str] = mapped_column(String, default="Zone A")
    task_type: Mapped[str] = mapped_column(String)
    priority: Mapped[str] = mapped_column(String, default="Medium")
    shift_date: Mapped[dt.date] = mapped_column(Date)
    planned_start: Mapped[dt.datetime] = mapped_column(DateTime)
    estimated_duration_min: Mapped[float] = mapped_column(Float)
    ai_predicted_duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="Not Started")
    dependencies: Mapped[str | None] = mapped_column(String, nullable=True)
    required_training: Mapped[str | None] = mapped_column(String, nullable=True)
    safety_requirements: Mapped[str | None] = mapped_column(String, nullable=True)


class TaskSession(Base):
    __tablename__ = "task_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"))
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"))
    task_type: Mapped[str] = mapped_column(String)
    weather: Mapped[str] = mapped_column(String)
    operator_skill: Mapped[str] = mapped_column(String)
    machine_age: Mapped[float] = mapped_column(Float)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime)
    ended_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    estimated_time_min: Mapped[float] = mapped_column(Float)
    actual_time_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    idle_time_min: Mapped[float] = mapped_column(Float, default=0)
    load_cycles: Mapped[int] = mapped_column(Integer, default=0)
    fuel_used_l: Mapped[float] = mapped_column(Float, default=0)
    progress_pct: Mapped[float] = mapped_column(Float, default=0)
    scenario_profile: Mapped[str] = mapped_column(String, default="normal_expert")


class OperationEvent(Base):
    __tablename__ = "operation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_session_id: Mapped[int] = mapped_column(ForeignKey("task_sessions.id"))
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime)
    event_type: Mapped[str] = mapped_column(String)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    event_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"))
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"))
    task_session_id: Mapped[int | None] = mapped_column(ForeignKey("task_sessions.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)  # Informational / Caution / Warning / Critical
    message: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    source_data: Mapped[str] = mapped_column(Text)
    triggered_at: Mapped[dt.datetime] = mapped_column(DateTime)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"))
    machine_id: Mapped[str | None] = mapped_column(ForeignKey("machines.id"), nullable=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    category: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="Reported")
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class EnvironmentSnapshot(Base):
    __tablename__ = "environment_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[str] = mapped_column(String, default="SITE01")
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime)
    weather: Mapped[str] = mapped_column(String)
    temperature_c: Mapped[float] = mapped_column(Float)
    wind_kph: Mapped[float] = mapped_column(Float)
    visibility: Mapped[str] = mapped_column(String)
    ground_condition: Mapped[str] = mapped_column(String)


class TrainingContent(Base):
    __tablename__ = "training_content"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)  # video / handbook / instructor / simulation / checklist
    machine_family: Mapped[str] = mapped_column(String)
    task_type: Mapped[str | None] = mapped_column(String, nullable=True)
    skill_level: Mapped[str] = mapped_column(String, default="All")
    duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_text: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String)


class TrainingRecord(Base):
    __tablename__ = "training_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"))
    training_content_id: Mapped[str] = mapped_column(ForeignKey("training_content.id"))
    status: Mapped[str] = mapped_column(String, default="Not Started")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)


class InstructorSlot(Base):
    __tablename__ = "instructor_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instructor_name: Mapped[str] = mapped_column(String)
    expertise: Mapped[str] = mapped_column(String)
    topic: Mapped[str] = mapped_column(String)
    mode: Mapped[str] = mapped_column(String)  # Virtual / Onsite
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    start_time: Mapped[dt.datetime] = mapped_column(DateTime)
    end_time: Mapped[dt.datetime] = mapped_column(DateTime)
    booked_by_operator_id: Mapped[str | None] = mapped_column(ForeignKey("operators.id"), nullable=True)


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_session_id: Mapped[int] = mapped_column(ForeignKey("task_sessions.id"))
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.id"))
    dimension: Mapped[str] = mapped_column(String)
    baseline_value: Mapped[float] = mapped_column(Float)
    actual_value: Mapped[float] = mapped_column(Float)
    deviation_score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    possible_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="Detected")
    feedback_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class EtaPrediction(Base):
    __tablename__ = "eta_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    point_estimate_min: Mapped[float] = mapped_column(Float)
    low_estimate_min: Mapped[float] = mapped_column(Float)
    high_estimate_min: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String)
    top_factors: Mapped[str] = mapped_column(Text)  # JSON-encoded list
    predicted_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class EtaOutcome(Base):
    __tablename__ = "eta_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eta_prediction_id: Mapped[int] = mapped_column(ForeignKey("eta_predictions.id"))
    actual_duration_min: Mapped[float] = mapped_column(Float)
    error_min: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
