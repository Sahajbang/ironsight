"""Recommendation rules for the dashboard and the training hub.

Every recommendation carries the reason and the data that triggered it (PRD §7.3, §10.2) —
a recommendation the operator can't audit is just noise.
"""
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.services import context, rules

SEVERITY_RANK = {"Critical": 0, "Warning": 1, "Caution": 2, "Informational": 3}


def next_best_actions(db: Session, operator_id: str, limit: int = 3) -> list[dict]:
    actions: list[dict] = []
    alerts = rules.evaluate(db, operator_id)
    current = context.get_current_task(db, operator_id)
    upcoming = context.get_next_task(db, operator_id)
    env = context.get_latest_environment(db)

    blocking = [a for a in alerts if a["severity"] in ("Critical", "Warning")]
    for alert in blocking[:1]:
        actions.append({
            "id": f"resolve-{alert['event_type']}",
            "title": f"Resolve: {alert['message']}",
            "reason": alert["reason"],
            "source": alert["source_data"],
            "severity": alert["severity"],
            "route": "/safety",
            "guide_id": "safety-alerts",
        })

    checklist_alert = next((a for a in alerts if a["event_type"] == "checklist_incomplete"), None)
    if checklist_alert:
        actions.append({
            "id": "complete-checklist",
            "title": "Complete the pre-operation checklist",
            "reason": checklist_alert["reason"],
            "source": checklist_alert["source_data"],
            "severity": "Caution",
            "route": "/safety",
            "guide_id": "start-checklist",
        })

    training = training_recommendations(db, operator_id, limit=1)
    if training:
        top = training[0]
        actions.append({
            "id": f"training-{top['content']['id']}",
            "title": f"Recommended before this task: {top['content']['title']}",
            "reason": top["reason"],
            "source": top["trigger"],
            "severity": "Informational",
            "route": "/training",
            "guide_id": "training-recommendations",
        })

    if env and (env.weather in ("Rainy", "Windy") or env.ground_condition == "Wet"):
        actions.append({
            "id": "weather-risk",
            "title": f"{env.weather} conditions may increase task duration",
            "reason": "Wet or windy conditions slow excavation and trenching cycles, which pushes the predicted finish time out.",
            "source": f"weather={env.weather}, ground_condition={env.ground_condition}",
            "severity": "Informational",
            "route": "/",
            "guide_id": "task-eta",
        })

    last_session = next(iter(context.get_recent_sessions(db, operator_id, limit=1)), None)
    if last_session and last_session.actual_time_min:
        idle_ratio = last_session.idle_time_min / last_session.actual_time_min
        if idle_ratio > 0.35:
            actions.append({
                "id": "idle-review",
                "title": f"High idle time on your last {last_session.task_type.lower()} task",
                "reason": f"{last_session.idle_time_min:.0f} min of the {last_session.actual_time_min:.0f} min task was idle ({idle_ratio:.0%}).",
                "source": f"task_session_id={last_session.id}",
                "severity": "Informational",
                "route": "/insights",
                "guide_id": "anomaly-list",
            })

    if not current and upcoming:
        actions.append({
            "id": "start-task",
            "title": f"Start {upcoming.task_type.lower()} task",
            "reason": f"Scheduled for {upcoming.planned_start.strftime('%H:%M')} in {upcoming.zone}, priority {upcoming.priority.lower()}.",
            "source": f"task_id={upcoming.id}",
            "severity": "Informational",
            "route": "/",
            "guide_id": "task-timeline",
        })

    actions.sort(key=lambda a: SEVERITY_RANK.get(a["severity"], 9))
    return actions[:limit]


def training_recommendations(db: Session, operator_id: str, limit: int = 4) -> list[dict]:
    operator = context.get_operator(db, operator_id)
    machine = context.get_machine_for_operator(db, operator_id)
    task = context.get_current_task(db, operator_id) or context.get_next_task(db, operator_id)

    completed = {
        r.training_content_id for r in db.scalars(
            select(m.TrainingRecord).where(
                m.TrainingRecord.operator_id == operator_id, m.TrainingRecord.status == "Completed"
            )
        )
    }
    catalog = list(db.scalars(select(m.TrainingContent)))
    by_id = {c.id: c for c in catalog}
    recommendations: list[dict] = []
    seen: set[str] = set()

    def add(content: m.TrainingContent, reason: str, trigger: str, priority: int) -> None:
        if content.id in seen or content.id in completed:
            return
        seen.add(content.id)
        recommendations.append({
            "content": {
                "id": content.id, "title": content.title, "content_type": content.content_type,
                "machine_family": content.machine_family, "task_type": content.task_type,
                "duration_min": content.duration_min, "url": content.url, "body_text": content.body_text,
            },
            "reason": reason,
            "trigger": trigger,
            "priority": priority,
        })

    # 1. Upcoming task needs a refresher
    if task:
        minutes_away = max(0, round((task.planned_start - dt.datetime.now()).total_seconds() / 60))
        for content in catalog:
            if content.task_type == task.task_type and content.content_type in ("video", "simulation"):
                when = f"in {minutes_away} minutes" if minutes_away else "now"
                add(content, f"You are scheduled for {task.task_type.lower()} {when}.",
                    f"task_id={task.id}", 1)

    # 2. Recent anomaly on this task type
    recent_anomalies = list(db.scalars(
        select(m.AnomalyEvent).where(m.AnomalyEvent.operator_id == operator_id,
                                     m.AnomalyEvent.status == "Detected")
        .order_by(m.AnomalyEvent.created_at.desc()).limit(3)
    ))
    for row in recent_anomalies:
        session = db.get(m.TaskSession, row.task_session_id)
        if not session:
            continue
        for content in catalog:
            if content.task_type == session.task_type and content.content_type == "video":
                add(content, row.explanation, f"anomaly_id={row.id}", 1)

    # 3. Recent safety events
    week_ago = dt.datetime.now() - dt.timedelta(days=7)
    events = list(db.scalars(
        select(m.SafetyEvent).where(m.SafetyEvent.operator_id == operator_id,
                                    m.SafetyEvent.triggered_at >= week_ago)
    ))
    if any(e.event_type.startswith("proximity") for e in events) and "TRN-instructor-proximity" in by_id:
        count = sum(1 for e in events if e.event_type.startswith("proximity"))
        add(by_id["TRN-instructor-proximity"],
            f"{count} proximity alert(s) recorded in the last 7 days.", "safety_events", 1)

    # 4. Skill level / machine familiarity
    if operator and operator.skill_level == "Beginner":
        for content in catalog:
            if content.skill_level == "Beginner" and (
                not machine or content.machine_family in (machine.machine_type, "All")
            ):
                add(content, "Recommended for operators at beginner skill level.",
                    f"skill_level={operator.skill_level}", 2)

    recommendations.sort(key=lambda r: r["priority"])
    return recommendations[:limit]
