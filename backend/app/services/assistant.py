"""AI Operator Companion (PRD §14, §21).

The LLM is NVIDIA Nemotron behind the OpenAI-compatible API. It never touches application
state directly: it can only call the deterministic tools registered below, and any UI
guidance it asks for is validated against the guide registry before it reaches the browser.

If no API key is configured, or the provider call fails, we fall back to a deterministic
keyword router that answers from the same tools — so the product stays usable with the AI
service down (PRD §23), which is also what makes the demo safe offline.
"""
import datetime as dt
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL
from app.services import anomaly, context, eta as eta_service, guide_registry, rules, search
from app.services.simulation import simulation

MAX_ROUNDS = 4
MAX_TOOL_CHARS = 4000

TOOLS = [
    {"type": "function", "function": {
        "name": "get_current_task",
        "description": "Get the operator's current or next task today, with status, zone and planned time.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_machine_status",
        "description": "Live machine state: seatbelt, proximity distance, operating state, zone.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_safety_events",
        "description": "Active safety alerts for the operator right now, plus recent logged safety events.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "search_training",
        "description": "Search training content: videos, simulations and instructor sessions.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "search_manuals",
        "description": "Search authoritative handbooks, checklists and safety procedures. Use this before answering any 'how do I...' question about operating the machine.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "get_eta",
        "description": "Predicted completion range and contributing factors for a task.",
        "parameters": {"type": "object", "properties": {"task_id": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "get_anomaly",
        "description": "Recently detected unusual operating patterns for this operator, with explanations.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "start_ui_guidance",
        "description": "Visually guide the operator to a control in the app. Use the exact target id from the allowed list. This only points at the control — it never activates it.",
        "parameters": {"type": "object", "properties": {
            "target": {"type": "string", "description": "Guide target id, e.g. report-incident"},
            "message": {"type": "string", "description": "Short instruction shown next to the highlighted control."},
        }, "required": ["target", "message"]},
    }},
    {"type": "function", "function": {
        "name": "navigate_to",
        "description": "Open a page in the app.",
        "parameters": {"type": "object", "properties": {"route": {"type": "string"}}, "required": ["route"]},
    }},
]


def _json_safe(value):
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


# ---------------------------------------------------------------- tools

def _tool_get_current_task(db: Session, operator_id: str, _args: dict) -> dict:
    task = context.get_current_task(db, operator_id) or context.get_next_task(db, operator_id)
    if task is None:
        return {"message": "No task scheduled for today."}
    session = context.get_session_for_task(db, task.id)
    return context.serialize_task(task, session)


def _tool_get_machine_status(db: Session, operator_id: str, _args: dict) -> dict:
    machine = context.get_machine_for_operator(db, operator_id)
    return {"machine": context.serialize_machine(machine), "live": simulation.machine_state(operator_id)}


def _tool_get_safety_events(db: Session, operator_id: str, _args: dict) -> dict:
    active = rules.evaluate(db, operator_id)
    recent = list(db.scalars(
        select(m.SafetyEvent)
        .where(m.SafetyEvent.operator_id == operator_id)
        .order_by(m.SafetyEvent.triggered_at.desc())
        .limit(5)
    ))
    return {
        "active_alerts": active,
        "recent_events": [
            {"event_type": e.event_type, "severity": e.severity, "message": e.message, "triggered_at": e.triggered_at}
            for e in recent
        ],
    }


def _search_tool(db: Session, operator_id: str, query: str, content_types: set[str] | None) -> dict:
    task = context.get_current_task(db, operator_id) or context.get_next_task(db, operator_id)
    machine = context.get_machine_for_operator(db, operator_id)
    operator = context.get_operator(db, operator_id)
    results = search.index.search(
        db, query, limit=5,
        machine_type=machine.machine_type if machine else None,
        task_type=task.task_type if task else None,
        skill_level=operator.skill_level if operator else None,
    )
    if content_types:
        results = [r for r in results if r["content_type"] in content_types]
    return {"query": query, "results": [
        {"id": r["id"], "title": r["title"], "type": r["result_type"], "url": r["url"], "text": r["body_text"]}
        for r in results
    ]}


def _tool_get_eta(db: Session, operator_id: str, args: dict) -> dict:
    task_id = args.get("task_id")
    task = db.get(m.Task, task_id) if task_id else None
    if task is None:
        task = context.get_current_task(db, operator_id) or context.get_next_task(db, operator_id)
    if task is None:
        return {"message": "No task available to estimate."}
    prediction = eta_service.predict_for_task(db, task)
    return {"task_id": task.id, "task_type": task.task_type, **prediction}


def _tool_get_anomaly(db: Session, operator_id: str, _args: dict) -> dict:
    rows = list(db.scalars(
        select(m.AnomalyEvent)
        .where(m.AnomalyEvent.operator_id == operator_id)
        .order_by(m.AnomalyEvent.created_at.desc())
        .limit(3)
    ))
    return {"anomalies": [anomaly.serialize(db, row) for row in rows]}


# ---------------------------------------------------------------- prompt

def _system_prompt(db: Session, operator_id: str, route: str | None) -> str:
    operator = context.get_operator(db, operator_id)
    machine = context.get_machine_for_operator(db, operator_id)
    task = context.get_current_task(db, operator_id) or context.get_next_task(db, operator_id)
    env = context.get_latest_environment(db)
    alerts = rules.evaluate(db, operator_id)
    targets = ", ".join(guide_registry.GUIDE_TARGETS)

    lines = [
        "You are Ironsight, an in-cab assistant for heavy-equipment operators (excavators and loaders).",
        "Answer in at most three short sentences. Plain operator language, no marketing tone, no emoji.",
        "",
        "CONTEXT",
        f"- Operator: {operator.name if operator else operator_id} ({operator.skill_level if operator else 'unknown'} level)",
        f"- Machine: {machine.model + ' ' + machine.machine_type if machine else 'unknown'}",
        f"- Task: {task.task_type + ' in ' + task.zone + ' (' + task.status + ')' if task else 'none scheduled'}",
        f"- Weather: {env.weather + ', ' + env.ground_condition + ' ground' if env else 'unknown'}",
        f"- Active safety alerts: {', '.join(a['event_type'] for a in alerts) if alerts else 'none'}",
        f"- Current screen: {route or 'unknown'}",
        "",
        "RULES",
        "- For any question about how to operate the machine or follow a procedure, call search_manuals first and answer from what it returns. Cite the document title. Do not invent procedures.",
        "- Safety alerts come from the app's own rule engine. Report them; never invent, downgrade or dismiss one.",
        "- When the operator asks how to do something in this app, call start_ui_guidance so the pointer walks them to the control, then say one sentence about what to do there.",
        f"- Valid start_ui_guidance targets: {targets}",
        "- You can point at a control. You must never submit a report, acknowledge a critical alert, change a threshold, or operate the machine.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- main entry

def chat(db: Session, message: str, operator_id: str = "OP1001", route: str | None = None,
         task_id: str | None = None) -> dict:
    guide_actions: list[dict] = []
    sources: list[dict] = []

    def run_tool(name: str, args: dict) -> dict:
        if name == "get_current_task":
            return _tool_get_current_task(db, operator_id, args)
        if name == "get_machine_status":
            return _tool_get_machine_status(db, operator_id, args)
        if name == "get_safety_events":
            return _tool_get_safety_events(db, operator_id, args)
        if name == "search_training":
            result = _search_tool(db, operator_id, args.get("query", ""), {"video", "simulation", "instructor"})
            sources.extend(result["results"])
            return result
        if name == "search_manuals":
            result = _search_tool(db, operator_id, args.get("query", ""), {"handbook", "checklist"})
            sources.extend(result["results"])
            return result
        if name == "get_eta":
            return _tool_get_eta(db, operator_id, args)
        if name == "get_anomaly":
            return _tool_get_anomaly(db, operator_id, args)
        if name == "start_ui_guidance":
            plan = guide_registry.plan_for_target(args.get("target", ""), args.get("message", ""))
            guide_actions.extend(plan)
            return {"ok": bool(plan), "steps": len(plan),
                    "note": "Pointer queued." if plan else "Unknown guide target — pick one from the allowed list."}
        if name == "navigate_to":
            actions = guide_registry.validate_actions(
                [{"action": "navigate", "target": None, "route": args.get("route"), "message": "", "waitForUser": False}]
            )
            guide_actions.extend(actions)
            return {"ok": bool(actions)}
        return {"error": f"unknown tool {name}"}

    if not NVIDIA_API_KEY:
        return _fallback(db, message, operator_id, reason="NVIDIA_API_KEY not configured")

    try:
        from openai import OpenAI

        client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY, timeout=45.0)
        messages: list[dict] = [
            {"role": "system", "content": _system_prompt(db, operator_id, route)},
            {"role": "user", "content": message if not task_id else f"{message}\n(task_id: {task_id})"},
        ]
        tools_used: list[str] = []
        reply = ""

        for _ in range(MAX_ROUNDS):
            response = client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=messages,
                tools=TOOLS,
                temperature=0.2,
                top_p=0.95,
                max_tokens=900,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            choice = response.choices[0].message
            tool_calls = getattr(choice, "tool_calls", None)

            if not tool_calls:
                reply = (choice.content or "").strip()
                break

            messages.append({
                "role": "assistant",
                "content": choice.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in tool_calls
                ],
            })
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = run_tool(tc.function.name, args)
                tools_used.append(tc.function.name)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(_json_safe(result))[:MAX_TOOL_CHARS],
                })

        if not reply:
            reply = "I pulled up what I could — check the highlighted panel for the details."

        return {
            "reply": reply,
            "guide_actions": guide_actions,
            "tools_used": tools_used,
            "sources": sources[:5],
            "source": "nemotron",
            "model": NVIDIA_MODEL,
            "degraded": False,
        }

    except Exception as exc:  # provider down, bad key, rate limit, tool-calling unsupported
        return _fallback(db, message, operator_id, reason=f"{type(exc).__name__}: {exc}"[:200])


# ---------------------------------------------------------------- deterministic fallback

INTENTS = [
    ("report-incident", ("report", "incident", "log this", "near miss", "accident")),
    ("start-checklist", ("checklist", "pre-op", "pre operation", "preoperation", "inspection")),
    ("safety-alerts", ("safety", "alert", "hazard", "seatbelt", "proximity", "warning", "danger")),
    ("training-recommendations", ("training", "learn", "refresher", "course", "video", "practice", "simulator")),
    ("book-instructor", ("instructor", "book", "session", "trainer")),
    ("task-eta", ("eta", "how long", "finish", "done by", "estimate", "time left")),
    ("anomaly-list", ("idle", "anomaly", "unusual", "abnormal", "why is my", "behaviour", "behavior")),
    ("site-map", ("map", "where is", "site", "jobsite", "who else")),
    ("current-task", ("task", "what should i do", "next", "shift", "schedule")),
]


def _fallback(db: Session, message: str, operator_id: str, reason: str) -> dict:
    text = message.lower()
    target = next((t for t, keywords in INTENTS if any(k in text for k in keywords)), None)

    if target == "safety-alerts":
        alerts = rules.evaluate(db, operator_id)
        reply = (f"{len(alerts)} active alert(s): " + "; ".join(f"{a['severity']} — {a['message']}" for a in alerts[:2])
                 if alerts else "No active safety alerts right now.")
    elif target == "task-eta":
        task = context.get_current_task(db, operator_id) or context.get_next_task(db, operator_id)
        if task:
            prediction = eta_service.predict_for_task(db, task)
            factors = ", ".join(f["name"].lower() for f in prediction["top_factors"][:2]) or "planned duration"
            reply = (f"{task.task_type}: estimated completion {eta_service.format_range(prediction)} "
                     f"({prediction['confidence'].lower()} confidence). Main factors: {factors}.")
        else:
            reply = "No task scheduled to estimate."
    elif target == "anomaly-list":
        rows = list(db.scalars(
            select(m.AnomalyEvent).where(m.AnomalyEvent.operator_id == operator_id)
            .order_by(m.AnomalyEvent.created_at.desc()).limit(1)
        ))
        reply = rows[0].explanation if rows else "No unusual operating patterns detected recently."
    elif target == "report-incident":
        reply = "I'll take you to the incident form. Fill in what happened — you submit it, not me."
    elif target == "start-checklist":
        reply = "Here's the pre-operation checklist for your next task. Work through every item before you start."
    elif target in ("training-recommendations", "book-instructor"):
        grouped = search.grouped_search(db, message, limit=3)
        titles = ", ".join(r["title"] for r in grouped["results"][:2])
        reply = f"Training that matches: {titles}." if titles else "Opening the training hub."
    else:
        grouped = search.grouped_search(db, message, limit=3)
        if grouped["quick_answer"]:
            reply = f"{grouped['quick_answer']['text']} (from {grouped['quick_answer']['source_title']})"
            target = target or "search-bar"
        else:
            task = context.get_current_task(db, operator_id) or context.get_next_task(db, operator_id)
            reply = (f"Your next task is {task.task_type} in {task.zone}." if task
                     else "Nothing scheduled right now. Try Search for manuals and procedures.")
            target = target or "current-task"

    guide_actions = guide_registry.plan_for_target(target, reply[:90]) if target else []
    return {
        "reply": reply,
        "guide_actions": guide_actions,
        "tools_used": ["fallback_router"],
        "sources": [],
        "source": "fallback",
        "model": None,
        "degraded": True,
        "degraded_reason": reason,
    }


def guide(target: str, message: str | None = None) -> dict:
    entry = guide_registry.get_target(target)
    if entry is None:
        return {"target": target, "actions": [], "error": "unknown guide target"}
    return {
        "target": target,
        "purpose": entry["purpose"],
        "actions": guide_registry.plan_for_target(target, message or entry["purpose"]),
    }
