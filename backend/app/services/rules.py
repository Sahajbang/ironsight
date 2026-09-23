"""Deterministic safety rule engine (PRD §9).

Every alert is produced by explicit rules over live simulated telemetry + DB history —
never by the LLM (PRD §23: "Safety alerts must not depend solely on an LLM"). Each alert
answers the five questions from §9.3: what happened, why it matters, what to do, how long
it has been true, and what data triggered it.
"""
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.services import context
from app.services.simulation import simulation

SEVERITY_ORDER = {"Critical": 0, "Warning": 1, "Caution": 2, "Informational": 3}

BASE_CHECKLIST = [
    "Seatbelt and ROPS condition verified",
    "Walkaround inspection completed",
    "Fluid levels checked",
    "Mirrors and cameras clean and aligned",
    "Horn and travel alarm tested",
]

TASK_CHECKLIST = {
    "Trenching": [
        "Utility locates confirmed",
        "Trench line marked",
        "Spoil setback distance verified",
    ],
    "Earth Excavation": [
        "Swing radius clear of personnel",
        "Spoil pile placement confirmed",
    ],
    "Material Loading": [
        "Load path clear of personnel",
        "Haul truck coordination confirmed",
    ],
    "Grading": [
        "Grade stakes visible",
        "Blade/bucket angle set",
    ],
    "Demolition": [
        "Structural hazard zone marked",
        "Debris fall radius clear",
        "Spotter positioned",
    ],
}


def generate_checklist(machine_type: str | None, task_type: str | None, env: m.EnvironmentSnapshot | None) -> list[str]:
    items = list(BASE_CHECKLIST)
    items.extend(TASK_CHECKLIST.get(task_type or "", []))
    if machine_type == "Loader":
        items.append("Tire condition and pressure checked")
    if env is not None:
        if env.weather == "Rainy" or env.ground_condition == "Wet":
            items.append("Wet-ground traction and visibility assessed")
        if env.wind_kph and env.wind_kph > 25:
            items.append("High-wind working limits reviewed")
    return items


def checklist_completed(db: Session, operator_id: str, task_id: str | None) -> bool:
    if task_id is None:
        return False
    stmt = select(m.SafetyEvent).where(
        m.SafetyEvent.operator_id == operator_id,
        m.SafetyEvent.event_type == "checklist_completed",
        m.SafetyEvent.source_data.like(f"%{task_id}%"),
    )
    return db.scalars(stmt).first() is not None


def _alert(key: str, severity: str, message: str, reason: str, action: str, source: str,
           duration_min: float | None = None, triggered_at: dt.datetime | None = None) -> dict:
    return {
        "id": key,
        "event_type": key,
        "severity": severity,
        "message": message,
        "reason": reason,
        "recommended_action": action,
        "source_data": source,
        "duration_min": duration_min,
        "triggered_at": triggered_at or dt.datetime.now(),
    }


def evaluate(db: Session, operator_id: str) -> list[dict]:
    """Run every safety rule for an operator and return active alerts, worst first."""
    alerts: list[dict] = []
    live = simulation.machine_state(operator_id)
    sim_state = simulation.operator_state(operator_id)
    env = context.get_latest_environment(db)
    current_task = context.get_current_task(db, operator_id)
    next_task = current_task or context.get_next_task(db, operator_id)
    machine = context.get_machine_for_operator(db, operator_id)
    now = dt.datetime.now()

    # A. Seatbelt compliance
    if live.get("seatbelt_status") == "Unfastened" and live.get("engine_on"):
        alerts.append(_alert(
            "seatbelt_unfastened", "Warning",
            "Seatbelt unfastened while the machine is active.",
            "Operating without a fastened seatbelt sharply increases injury risk in a sudden stop, slide or rollover.",
            "Stop work and fasten the seatbelt before continuing operation.",
            f"seatbelt_status={live.get('seatbelt_status')}, engine_on={live.get('engine_on')}",
        ))

    # B. Proximity hazards (progressive levels)
    distance = live.get("proximity_distance_m")
    if distance is not None:
        if distance < 3.0:
            alerts.append(_alert(
                "proximity_critical", "Critical",
                f"Personnel or equipment detected {distance} m from the machine.",
                "At this range there is not enough clearance to stop safely if the machine or the person moves.",
                "Stop all travel and swing immediately. Confirm the area is clear before resuming.",
                f"proximity_distance_m={distance}, threshold=3.0",
            ))
        elif distance < 6.0:
            alerts.append(_alert(
                "proximity_warning", "Warning",
                f"Personnel or equipment detected {distance} m from the machine.",
                "Reduced clearance raises collision risk during swing or travel.",
                "Slow down, maintain visual contact and be ready to stop.",
                f"proximity_distance_m={distance}, threshold=6.0",
            ))

    # G. Pre-operation safety checklist
    if next_task is not None and next_task.safety_requirements and not checklist_completed(db, operator_id, next_task.id):
        alerts.append(_alert(
            "checklist_incomplete", "Caution",
            f"Pre-operation checklist not completed for {next_task.task_type}.",
            "The checklist catches machine and site defects before they become incidents, and completion is auditable.",
            "Open the pre-operation checklist and complete every item before starting the task.",
            f"task_id={next_task.id}, safety_requirements={next_task.safety_requirements}",
        ))

    # D. Fatigue / distraction risk
    hours_on_shift = (now - context.shift_start(now)).total_seconds() / 3600
    if hours_on_shift >= 9:
        alerts.append(_alert(
            "fatigue_risk", "Warning",
            f"Shift duration has reached {hours_on_shift:.1f} hours.",
            "Extended time on task without a break raises reaction time and error rate. This is a risk indicator, not a medical assessment.",
            "Take a scheduled break before starting the next task.",
            f"hours_on_shift={hours_on_shift:.1f}, threshold=9",
            duration_min=round(hours_on_shift * 60, 0),
        ))
    elif hours_on_shift >= 6:
        alerts.append(_alert(
            "fatigue_risk", "Caution",
            f"Shift duration has reached {hours_on_shift:.1f} hours.",
            "Attention typically degrades after sustained operation. This is a risk indicator, not a medical assessment.",
            "Plan a short break within the next task changeover.",
            f"hours_on_shift={hours_on_shift:.1f}, threshold=6",
            duration_min=round(hours_on_shift * 60, 0),
        ))

    # E. Unsafe operating pattern detection
    week_ago = now - dt.timedelta(days=7)
    recent_events = list(db.scalars(
        select(m.SafetyEvent).where(
            m.SafetyEvent.operator_id == operator_id,
            m.SafetyEvent.triggered_at >= week_ago,
            m.SafetyEvent.event_type.in_(["seatbelt_unfastened", "proximity_warning"]),
        )
    ))
    if len(recent_events) >= 3:
        kinds = {e.event_type for e in recent_events}
        alerts.append(_alert(
            "unsafe_pattern", "Caution",
            f"{len(recent_events)} safety events recorded in the last 7 days.",
            "Repeated events of the same kind usually point at a habit or a site condition rather than a one-off.",
            "Review the safety timeline and consider the matching refresher in the Training Hub.",
            f"event_count_7d={len(recent_events)}, types={sorted(kinds)}",
        ))

    # F. Safe-zone / geofence awareness
    sim_zone = live.get("zone")
    if sim_zone == "Restricted":
        alerts.append(_alert(
            "geofence_breach", "Critical",
            "Machine position is inside a restricted area.",
            "Restricted areas are closed to equipment because of buried services, unstable ground or overhead hazards.",
            "Stop and reverse out of the restricted area along the route you entered.",
            f"zone={sim_zone}",
        ))
    elif next_task is not None and sim_zone and sim_zone != next_task.zone:
        alerts.append(_alert(
            "geofence_drift", "Caution",
            f"Machine is in {sim_zone} but the assigned task is in {next_task.zone}.",
            "Working outside the assigned zone can put the machine into another crew's work area.",
            f"Return to {next_task.zone} or confirm the task assignment has changed.",
            f"current_zone={sim_zone}, expected_zone={next_task.zone}",
        ))

    # H. Environmental hazard awareness (facts separated from the recommendation)
    if env is not None:
        if env.visibility == "Poor":
            alerts.append(_alert(
                "environmental_visibility", "Warning",
                f"Site visibility is reported as {env.visibility}.",
                "Reduced visibility makes ground personnel and obstacles harder to see from the cab.",
                "Reduce travel speed and use a spotter for blind movements.",
                f"visibility={env.visibility}, weather={env.weather}",
            ))
        if env.weather == "Rainy" or env.ground_condition == "Wet":
            alerts.append(_alert(
                "environmental_ground", "Caution",
                f"Ground condition is {env.ground_condition} ({env.weather.lower()} weather).",
                "Wet ground reduces traction and stability, and typically lengthens excavation and trenching cycles.",
                "Reduce speed on grades and re-check bench stability before digging.",
                f"weather={env.weather}, ground_condition={env.ground_condition}",
            ))
        if env.wind_kph and env.wind_kph > 30:
            alerts.append(_alert(
                "environmental_wind", "Caution",
                f"Wind speed is {env.wind_kph} km/h.",
                "High wind affects suspended loads and raises dust, reducing visibility.",
                "Avoid lifting wide or light loads until the wind drops.",
                f"wind_kph={env.wind_kph}, threshold=30",
            ))
        if env.temperature_c and env.temperature_c >= 35:
            alerts.append(_alert(
                "environmental_heat", "Caution",
                f"Site temperature is {env.temperature_c} °C.",
                "Heat stress raises fatigue and dehydration risk over a full shift.",
                "Increase hydration and take breaks in shade between tasks.",
                f"temperature_c={env.temperature_c}, threshold=35",
            ))

    # Live simulated hazards (proximity zones, obstructions) raised by the site simulation
    for hazard in simulation.hazards_for(operator_id):
        alerts.append(_alert(
            f"hazard_{hazard['id']}", hazard["severity"],
            hazard["message"],
            "An active hazard zone overlaps your current work area.",
            "Acknowledge the hazard and keep clear until it is cleared by the site.",
            f"hazard_id={hazard['id']}, zone={hazard['zone']}, source={hazard['source']}",
            duration_min=round((now - hazard["created_at"]).total_seconds() / 60, 1),
            triggered_at=hazard["created_at"],
        ))

    _ = sim_state, machine  # context available for future rules; intentionally unused here
    alerts.sort(key=lambda a: SEVERITY_ORDER.get(a["severity"], 9))
    return alerts


def record_alerts(db: Session, operator_id: str, alerts: list[dict]) -> int:
    """Persist newly-raised alerts to safety_events so the timeline has history.

    Deduplicated: an alert of the same type already logged and unresolved in the last
    30 minutes is treated as the same ongoing condition rather than a new event.
    """
    machine = context.get_machine_for_operator(db, operator_id)
    session = context.get_active_session(db, operator_id)
    cutoff = dt.datetime.now() - dt.timedelta(minutes=30)
    written = 0

    for alert in alerts:
        if alert["severity"] == "Informational":
            continue
        existing = db.scalars(
            select(m.SafetyEvent).where(
                m.SafetyEvent.operator_id == operator_id,
                m.SafetyEvent.event_type == alert["event_type"],
                m.SafetyEvent.triggered_at >= cutoff,
            )
        ).first()
        if existing is not None:
            continue
        db.add(m.SafetyEvent(
            operator_id=operator_id,
            machine_id=machine.id if machine else "EXC001",
            task_session_id=session.id if session else None,
            event_type=alert["event_type"],
            severity=alert["severity"],
            message=alert["message"],
            reason=alert["reason"],
            recommended_action=alert["recommended_action"],
            source_data=alert["source_data"],
            triggered_at=alert["triggered_at"],
        ))
        written += 1

    if written:
        db.commit()
    return written
