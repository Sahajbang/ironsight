"""Registry of UI elements the AI Guide is allowed to point at (PRD §14.3).

The LLM never invents a CSS selector. It can only name a key from this registry; anything
else is dropped during validation. Restricted actions (submitting a report, acknowledging a
critical alert, changing a safety threshold, any machine control) are deliberately absent —
the guide can move attention to a control, never operate it.
"""

ALLOWED_ACTIONS = {"navigate", "scroll", "highlight", "explain", "tooltip"}

RESTRICTED_ACTIONS = {"submit", "acknowledge", "confirm", "change_threshold", "machine_control", "click"}

GUIDE_TARGETS: dict[str, dict] = {
    # --- navigation rail: answers "where is X?" ---
    "nav-dashboard": {"route": "/", "purpose": "Dashboard tab in the left navigation rail.", "preconditions": []},
    "nav-site": {"route": "/site", "purpose": "Live Site tab in the left navigation rail.", "preconditions": []},
    "nav-tasks": {"route": "/tasks", "purpose": "Tasks tab in the left navigation rail.", "preconditions": []},
    "nav-safety": {"route": "/safety", "purpose": "Safety tab in the left navigation rail.", "preconditions": []},
    "nav-training": {"route": "/training", "purpose": "Training tab in the left navigation rail.", "preconditions": []},
    "nav-insights": {"route": "/insights", "purpose": "Insights tab in the left navigation rail.", "preconditions": []},
    "nav-estimator": {"route": "/estimator", "purpose": "Estimator tab in the left navigation rail.", "preconditions": []},
    "nav-incidents": {"route": "/incidents", "purpose": "Incidents tab in the left navigation rail.", "preconditions": []},

    "report-incident": {
        "route": "/incidents",
        "purpose": "Button that opens the incident report form.",
        "preconditions": [],
        "safety_note": "The guide may open the form but never submits it — the operator confirms every report.",
    },
    "incident-form": {
        "route": "/incidents",
        "purpose": "The incident report form fields: category, severity, location and description.",
        "preconditions": ["The report form has been opened."],
    },
    "incident-submit": {
        "route": "/incidents",
        "purpose": "Submit button on the incident report form.",
        "preconditions": ["The form has been filled in."],
        "safety_note": "The guide may point at this button but the operator presses it.",
    },
    "incident-list": {
        "route": "/incidents",
        "purpose": "List of logged incidents and their follow-up status.",
        "preconditions": [],
    },
    "checklist-confirm": {
        "route": "/safety",
        "purpose": "Button that confirms the pre-operation checklist is complete.",
        "preconditions": ["Every checklist item has been ticked."],
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


# Named walkthroughs. A single highlight answers "where is it"; a task like filing a report
# is several moves, and the operator should be led through all of them rather than dropped at
# the first button. Each step waits for the operator to act before the pointer moves on.
WORKFLOWS: dict[str, dict] = {
    "report_incident": {
        "label": "Report an incident",
        "steps": [
            ("report-incident", "Select Report Incident to open the form."),
            ("incident-form", "Set the category and severity, then describe what happened."),
            ("incident-submit", "Submit when you are ready — the report is yours to send."),
        ],
    },
    "pre_operation_checklist": {
        "label": "Complete the pre-operation checklist",
        "steps": [
            ("nav-safety", "Open the Safety tab."),
            ("start-checklist", "Work down the checklist and tick each item as you verify it."),
            ("checklist-confirm", "Confirm completion — this is recorded against the task."),
        ],
    },
    "find_training": {
        "label": "Find training for this task",
        "steps": [
            ("nav-training", "Open the Training tab."),
            ("training-recommendations", "These are recommended for you, each with the reason it was suggested."),
        ],
    },
    "check_eta": {
        "label": "See your predicted finish time",
        "steps": [
            ("nav-dashboard", "Go back to the Dashboard."),
            ("task-eta", "This is the predicted range and the factors driving it."),
        ],
    },
    "review_anomaly": {
        "label": "Review an unusual pattern",
        "steps": [
            ("nav-insights", "Open the Insights tab."),
            ("anomaly-list", "Here is what looked unusual against your own baseline."),
            ("anomaly-feedback", "If there was a good reason, tell the system — it learns from that."),
        ],
    },
    "find_safety": {
        "label": "Open the Safety centre",
        "steps": [
            ("nav-safety", "The Safety tab is here in the navigation rail."),
            ("safety-alerts", "Active alerts show here, each with what triggered it."),
        ],
    },
}


def plan_for_workflow(name: str) -> list[dict]:
    """Expand a named workflow into a validated step-by-step plan."""
    workflow = WORKFLOWS.get(name)
    if workflow is None:
        return []
    plan: list[dict] = []
    current_route: str | None = None
    for target_id, message in workflow["steps"]:
        target = GUIDE_TARGETS.get(target_id)
        if target is None:
            continue
        route = target["route"]
        if route != "*" and route != current_route:
            plan.append({"action": "navigate", "target": target_id, "route": route,
                         "message": "", "waitForUser": False})
            current_route = route
        plan.append({"action": "scroll", "target": target_id, "route": route, "message": "", "waitForUser": False})
        plan.append({"action": "highlight", "target": target_id, "route": route,
                     "message": message, "waitForUser": True})
    return validate_actions(plan)


def list_workflows() -> list[dict]:
    return [
        {"id": key, "label": value["label"], "steps": [s[0] for s in value["steps"]]}
        for key, value in WORKFLOWS.items()
    ]


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
