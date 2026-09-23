from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["Low", "Medium", "High"]
IncidentStatus = Literal["Reported", "Acknowledged", "Under Investigation", "Resolved"]


class IncidentCreate(BaseModel):
    operator_id: str
    machine_id: str | None = None
    task_id: str | None = None
    category: Literal["Near Miss", "Proximity", "Seatbelt", "Equipment Damage", "Other"]
    severity: Severity = "Medium"
    description: str = Field(min_length=3, max_length=2000)
    location: str
    photo_url: str | None = None


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus


class ChecklistCompleteRequest(BaseModel):
    operator_id: str
    completed_items: list[str] = Field(min_length=1)


class AnomalyFeedback(BaseModel):
    status: Literal["Confirmed Normal", "Confirmed Abnormal"]
    reason: str | None = Field(default=None, max_length=1000)


class EtaPredictRequest(BaseModel):
    task_type: str
    estimated_duration_min: float = Field(gt=0, le=1440)
    weather: str = "Sunny"
    operator_skill: str = "Intermediate"
    machine_age: float = Field(default=3.0, ge=0, le=40)
    operator_id: str | None = None


class BookingCreate(BaseModel):
    operator_id: str


class AssistantMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    operator_id: str = "OP1001"
    route: str | None = None
    task_id: str | None = None


class TaskStatusUpdate(BaseModel):
    status: Literal["Not Started", "Ready", "In Progress", "Blocked", "Completed"]


class TaskCompleteRequest(BaseModel):
    # Optional overrides so a demo can complete a task with realistic numbers instead of the
    # handful of real-world seconds that elapsed on stage.
    actual_time_min: float | None = Field(default=None, gt=0, le=1440)
    idle_time_min: float | None = Field(default=None, ge=0, le=1440)
