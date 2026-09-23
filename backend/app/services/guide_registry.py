"""Registry of UI elements the AI Guide is allowed to point at (PRD §14.3).

The LLM never invents a CSS selector. It can only name a key from this registry; anything
else is dropped during validation. Restricted actions (submitting a report, acknowledging a
critical alert, changing a safety threshold, any machine control) are deliberately absent —
the guide can move attention to a control, never operate it.
"""

ALLOWED_ACTIONS = {"navigate", "scroll", "highlight", "explain", "tooltip"}

RESTRICTED_ACTIONS = {"submit", "acknowledge", "confirm", "change_threshold", "machine_control", "click"}

GUIDE_TARGETS: dict[str, dict] = {
    "report-incident": {
        "route": "/incidents",
        "purpose": "Button that opens the incident report form.",
        "preconditions": [],
        "safety_note": "The guide may open the form but never submits it — the operator confirms every report.",
    },
    "incident-list": {
        "route": "/incidents",
        "purpose": "List of logged incidents and their follow-up status.",
        "preconditions": [],
    },
    "start-checklist": {
        "route": "/safety",
        "purpose": "Pre-operation safety checklist for the upcoming task.",
        "preconditions": ["A task with safety requirements is scheduled."],
    },
    "safety-alerts": {
        "route": "/safety",
        "purpose": "Live safety alert panel (seatbelt, proximity, environment, fatigue).",
        "preconditions": [],
    },
    "safety-timeline": {
        "route": "/safety",
        "purpose": "Chronological timeline of safety events across the shift.",
        "preconditions": [],
    },
    "current-task": {
        "route": "/",
        "purpose": "Current task panel with progress, elapsed time and live ETA.",
        "preconditions": ["A task is in progress."],
    },
    "task-timeline": {
        "route": "/",
        "purpose": "Today's task timeline on the dashboard.",
        "preconditions": [],
    },
    "task-eta": {
        "route": "/",
        "purpose": "Predicted completion range and the factors driving it.",
        "preconditions": [],
    },
    "next-best-action": {
        "route": "/",
        "purpose": "Recommended next action card on the dashboard.",
        "preconditions": [],
    },
    "open-training": {
        "route": "/training",
        "purpose": "Training hub with videos, handbooks, simulations and instructor booking.",
        "preconditions": [],
    },
    "training-recommendations": {
        "route": "/training",
        "purpose": "Training recommended for the operator right now, with the reason for each.",
        "preconditions": [],
    },
    "book-instructor": {
        "route": "/training",
        "purpose": "Instructor availability and booking.",
        "preconditions": [],
        "safety_note": "The guide may open booking but the operator confirms the slot.",
    },
    "search-bar": {
        "route": "*",
        "purpose": "Global search across manuals, procedures, training and checklists.",
        "preconditions": [],
    },
    "anomaly-list": {
        "route": "/insights",
        "purpose": "Detected unusual operating patterns with their explanations.",
        "preconditions": [],
    },
    "anomaly-feedback": {
        "route": "/insights",
        "purpose": "Controls to confirm an anomaly is normal or give the real reason.",
        "preconditions": ["At least one anomaly has been detected."],
    },
    "site-map": {
        "route": "/site",
        "purpose": "Live bird's-eye jobsite map with operators, hazards and incidents.",
        "preconditions": [],
    },
    "task-estimator": {
        "route": "/estimator",
        "purpose": "What-if task time estimator.",
        "preconditions": [],
    },
}


def list_targets() -> list[dict]:
    return [{"id": key, **value} for key, value in GUIDE_TARGETS.items()]


def get_target(target_id: str) -> dict | None:
    target = GUIDE_TARGETS.get(target_id)
    return {"id": target_id, **target} if target else None


def validate_actions(actions: list[dict]) -> list[dict]:
    """Drop anything the guide is not permitted to do before it reaches the UI (PRD §21)."""
    validated = []
    for action in actions:
        kind = action.get("action")
        if kind in RESTRICTED_ACTIONS or kind not in ALLOWED_ACTIONS:
            continue
        target = action.get("target")
        if kind != "navigate" and target not in GUIDE_TARGETS:
            continue
        entry = GUIDE_TARGETS.get(target, {})
        validated.append({
            "action": kind,
            "target": target,
            "route": action.get("route") or entry.get("route"),
            "message": action.get("message", ""),
            "waitForUser": bool(action.get("waitForUser", True)),
        })
    return validated


def plan_for_target(target_id: str, message: str) -> list[dict]:
    """Standard three-beat guide plan: go to the page, bring the control into view, highlight it."""
    target = GUIDE_TARGETS.get(target_id)
    if target is None:
        return []
    route = target["route"]
    plan = []
    if route != "*":
        plan.append({"action": "navigate", "target": target_id, "route": route,
                     "message": f"Opening {route}", "waitForUser": False})
    plan.append({"action": "scroll", "target": target_id, "route": route,
                 "message": "", "waitForUser": False})
    plan.append({"action": "highlight", "target": target_id, "route": route,
                 "message": message, "waitForUser": True})
    return validate_actions(plan)
