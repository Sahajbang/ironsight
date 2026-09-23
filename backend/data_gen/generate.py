"""Synthetic data generator for Ironsight.

Produces correlated operator/machine/task/safety history across the 8 behavior
scenario profiles from PRD §19, so the ETA model and anomaly baselines have real
signal (rain slows excavation, beginners overrun then improve, one operator runs
hot on idle time, another racks up safety alerts) instead of independent random
numbers.
"""
import datetime as dt
import json
import random
from statistics import median

random.seed(42)

SITE_ID = "SITE01"
TASK_TYPES = ["Earth Excavation", "Trenching", "Material Loading", "Grading", "Demolition"]
BASE_DURATION_MIN = {
    "Earth Excavation": 60,
    "Trenching": 50,
    "Material Loading": 30,
    "Grading": 35,
    "Demolition": 90,
}
WEATHER_OPTIONS = ["Sunny", "Sunny", "Cloudy", "Rainy", "Windy"]
ZONES = ["Zone A", "Zone B", "Zone C", "Zone D"]
HISTORY_DAYS = 20

OPERATORS = [
    {"id": "OP1001", "name": "Jordan Reyes", "skill_level": "Expert", "experience_years": 9.0, "profile": "normal_expert"},
    {"id": "OP1002", "name": "Casey Nguyen", "skill_level": "Beginner", "experience_years": 1.0, "profile": "beginner_improving"},
    {"id": "OP1003", "name": "Amir Osei", "skill_level": "Intermediate", "experience_years": 4.0, "profile": "excessive_idle"},
    {"id": "OP1004", "name": "Priya Shah", "skill_level": "Intermediate", "experience_years": 3.0, "profile": "repeated_safety_alerts"},
]

MACHINES = [
    {"id": "EXC001", "machine_type": "Excavator", "model": "Cat 320", "age_years": 2.0, "engine_hours": 1523.5},
    {"id": "EXC002", "machine_type": "Excavator", "model": "Cat 336", "age_years": 5.0, "engine_hours": 4210.0},
    {"id": "LDR001", "machine_type": "Loader", "model": "Cat 950", "age_years": 3.0, "engine_hours": 2890.0},
    {"id": "LDR002", "machine_type": "Loader", "model": "Cat 962", "age_years": 6.0, "engine_hours": 5230.0},
]

OPERATOR_MACHINE = {"OP1001": "EXC001", "OP1002": "LDR001", "OP1003": "EXC002", "OP1004": "LDR002"}

# Static training catalog (PRD §10.1) — also what the Search feature indexes, so wording
# is deliberately specific and varied rather than templated.
TRAINING_CATALOG = [
    {"id": "TRN-video-excavation", "title": "Earth Excavation Safety Refresher", "content_type": "video",
     "machine_family": "Excavator", "task_type": "Earth Excavation", "skill_level": "All", "duration_min": 6.0,
     "body_text": "A 6-minute refresher on excavation safety fundamentals: verifying bucket angle before each cut, "
                  "confirming spoil pile placement, and maintaining safe clearance from the excavation edge.",
     "url": "/training/video/earth-excavation-safety"},
    {"id": "TRN-video-trenching", "title": "Trenching Fundamentals Refresher", "content_type": "video",
     "machine_family": "Excavator", "task_type": "Trenching", "skill_level": "Beginner", "duration_min": 4.0,
     "body_text": "A 4-minute trenching fundamentals refresher covering correct bucket angle for consistent trench "
                  "depth, cycle pacing, and reducing idle time while waiting on haul trucks.",
     "url": "/training/video/trenching-fundamentals"},
    {"id": "TRN-video-loading", "title": "Material Loading Techniques", "content_type": "video",
     "machine_family": "Loader", "task_type": "Material Loading", "skill_level": "Beginner", "duration_min": 5.0,
     "body_text": "Covers efficient bucket fill technique, load cycle pacing, and coordinating with haul trucks to "
                  "reduce idle/waiting time during material loading.",
     "url": "/training/video/material-loading-techniques"},
    {"id": "TRN-video-grading", "title": "Grading Precision Basics", "content_type": "video",
     "machine_family": "All", "task_type": "Grading", "skill_level": "Intermediate", "duration_min": 5.0,
     "body_text": "Techniques for holding a consistent grade line, blade/bucket angle adjustments, and handling "
                  "wind-affected visibility during grading passes.",
     "url": "/training/video/grading-precision-basics"},
    {"id": "TRN-video-demolition", "title": "Demolition Hazard Awareness", "content_type": "video",
     "machine_family": "Excavator", "task_type": "Demolition", "skill_level": "Intermediate", "duration_min": 7.0,
     "body_text": "Covers structural collapse risk zones, debris fall radius, and proximity hazard response specific "
                  "to demolition tasks.",
     "url": "/training/video/demolition-hazard-awareness"},
    {"id": "TRN-manual-excavator", "title": "Excavator Operator Handbook", "content_type": "handbook",
     "machine_family": "Excavator", "task_type": None, "skill_level": "All", "duration_min": None,
     "body_text": "Full excavator operator reference: pre-operation inspection, seatbelt and ROPS requirements, "
                  "hydraulic control layout, bucket angle and attachment guidance, and troubleshooting basics for "
                  "the Cat 320/336 excavator family.",
     "url": "/training/handbook/excavator-operator-handbook"},
    {"id": "TRN-manual-loader", "title": "Loader Operator Handbook", "content_type": "handbook",
     "machine_family": "Loader", "task_type": None, "skill_level": "All", "duration_min": None,
     "body_text": "Full loader operator reference: pre-operation inspection, load cycle technique, tire and "
                  "undercarriage checks, and troubleshooting basics for the Cat 950/962 loader family.",
     "url": "/training/handbook/loader-operator-handbook"},
    {"id": "TRN-checklist-excavation", "title": "Earth Excavation Pre-Operation Checklist", "content_type": "checklist",
     "machine_family": "Excavator", "task_type": "Earth Excavation", "skill_level": "All", "duration_min": None,
     "body_text": "Quick-reference checklist: seatbelt fastened, swing area clear, spoil pile placement confirmed, "
                  "bucket condition inspected, proximity hazards checked before starting excavation.",
     "url": "/training/checklist/earth-excavation"},
    {"id": "TRN-checklist-trenching", "title": "Trenching Pre-Operation Checklist", "content_type": "checklist",
     "machine_family": "Excavator", "task_type": "Trenching", "skill_level": "All", "duration_min": None,
     "body_text": "Quick-reference checklist for trenching: trench line marked, utility locates confirmed, spoil "
                  "setback distance verified, seatbelt fastened, proximity alert zone checked before cutting.",
     "url": "/training/checklist/trenching"},
    {"id": "TRN-checklist-loading", "title": "Material Loading Checklist", "content_type": "checklist",
     "machine_family": "Loader", "task_type": "Material Loading", "skill_level": "All", "duration_min": None,
     "body_text": "Quick-reference checklist: bucket and tires inspected, haul truck coordination confirmed, load "
                  "path clear of personnel, seatbelt fastened.",
     "url": "/training/checklist/material-loading"},
    {"id": "TRN-checklist-grading", "title": "Grading Checklist", "content_type": "checklist",
     "machine_family": "All", "task_type": "Grading", "skill_level": "All", "duration_min": None,
     "body_text": "Quick-reference checklist: blade/bucket angle set, grade stakes visible, wind and visibility "
                  "checked, seatbelt fastened.",
     "url": "/training/checklist/grading"},
    {"id": "TRN-checklist-demolition", "title": "Demolition Checklist", "content_type": "checklist",
     "machine_family": "Excavator", "task_type": "Demolition", "skill_level": "All", "duration_min": None,
     "body_text": "Quick-reference checklist: structural hazard zone marked, debris fall radius clear, proximity "
                  "alert zone extended, seatbelt fastened, spotter positioned.",
     "url": "/training/checklist/demolition"},
    {"id": "TRN-instructor-trenching", "title": "Trenching Safety Fundamentals", "content_type": "instructor",
     "machine_family": "Excavator", "task_type": "Trenching", "skill_level": "All", "duration_min": 45.0,
     "body_text": "Instructor-led session covering trenching safety fundamentals, bucket angle technique, and "
                  "proximity hazard response for trenching operations.",
     "url": "/training/instructor/trenching-safety-fundamentals"},
    {"id": "TRN-instructor-loader", "title": "Loader Operation Essentials", "content_type": "instructor",
     "machine_family": "Loader", "task_type": "Material Loading", "skill_level": "Beginner", "duration_min": 45.0,
     "body_text": "Instructor-led session on loader operation essentials: load cycle technique, coordination with "
                  "haul trucks, and idle-time reduction strategies.",
     "url": "/training/instructor/loader-operation-essentials"},
    {"id": "TRN-instructor-proximity", "title": "Proximity Hazard Response", "content_type": "instructor",
     "machine_family": "All", "task_type": None, "skill_level": "All", "duration_min": 30.0,
     "body_text": "Instructor-led session on responding to proximity alerts: progressive warning levels, safe-stop "
                  "procedure, and when to report a near-miss incident.",
     "url": "/training/instructor/proximity-hazard-response"},
    {"id": "TRN-sim-excavation", "title": "Excavation Sequence Simulator", "content_type": "simulation",
     "machine_family": "Excavator", "task_type": "Earth Excavation", "skill_level": "All", "duration_min": 15.0,
     "body_text": "Interactive browser-based simulation of a full excavation sequence: digging, swinging, and "
                  "dumping cycles with bucket angle feedback and a simulated proximity hazard reaction scenario.",
     "url": "/training/simulation/excavation-sequence"},
    {"id": "TRN-sim-loader", "title": "Loading Cycle Simulator", "content_type": "simulation",
     "machine_family": "Loader", "task_type": "Material Loading", "skill_level": "All", "duration_min": 15.0,
     "body_text": "Interactive browser-based simulation of loader loading cycles, including hazard-response and "
                  "emergency/incident scenario practice.",
     "url": "/training/simulation/loading-cycle"},
]

INSTRUCTORS = [
    {"name": "Dana Whitfield", "expertise": "Excavator", "topics": ["Trenching Safety Fundamentals", "Excavator Operation Essentials"]},
    {"name": "Marcus Webb", "expertise": "Loader", "topics": ["Loader Operation Essentials", "Load Cycle Efficiency"]},
    {"name": "Elena Cruz", "expertise": "Safety", "topics": ["Proximity Hazard Response", "Incident Reporting Walkthrough"]},
]

# idle_ratio_boost: extra chance/size of an idle spike beyond the ~15% baseline
# duration_variance: gaussian noise stddev applied to actual-vs-estimated duration
# safety_alert_prob: chance of a safety event on a given session
PROFILE_PARAMS = {
    "normal_expert": dict(idle_spike_prob=0.05, duration_variance=0.06, safety_alert_prob=0.03),
    "beginner_improving": dict(idle_spike_prob=0.10, duration_variance=0.18, safety_alert_prob=0.10),
    "excessive_idle": dict(idle_spike_prob=0.40, duration_variance=0.10, safety_alert_prob=0.04),
    "repeated_safety_alerts": dict(idle_spike_prob=0.10, duration_variance=0.12, safety_alert_prob=0.35),
}

_ids = {"session": 0}


def _next_session_id() -> int:
    _ids["session"] += 1
    return _ids["session"]


def _weather_factor(weather: str, task_type: str) -> float:
    if weather == "Rainy" and task_type in ("Earth Excavation", "Trenching", "Demolition"):
        return 1.15
    if weather == "Windy" and task_type == "Grading":
        return 1.08
    return 1.0


def _make_session(operator: dict, machine: dict, task_id: str, task_type: str, when: dt.datetime,
                   weather: str, elapsed_days: int, in_progress: bool = False) -> tuple[dict, list[dict], list[dict]]:
    profile = operator["profile"]
    params = PROFILE_PARAMS[profile]
    base = BASE_DURATION_MIN[task_type]
    estimated = round(base * random.uniform(0.92, 1.08), 1)

    base_idle_frac = random.uniform(0.12, 0.18)
    idle_frac = base_idle_frac
    context = None
    if random.random() < params["idle_spike_prob"]:
        idle_frac = random.uniform(0.45, 0.65)
        context = "excessive_idle"
    elif random.random() < 0.08:
        idle_frac = random.uniform(0.40, 0.55)
        context = "truck_wait"
    idle_time_min = round(estimated * idle_frac, 1)

    skill_overrun = 0.0
    if profile == "beginner_improving":
        skill_overrun = max(0.02, 0.35 - 0.017 * elapsed_days)

    variance = random.gauss(0, params["duration_variance"])
    weather_factor = _weather_factor(weather, task_type)
    actual = estimated * (1 + variance + skill_overrun) * weather_factor
    actual += idle_time_min - estimated * 0.15
    actual = round(max(actual, estimated * 0.5), 1)

    load_cycles = max(1, int(round((estimated / 5) * random.uniform(0.8, 1.2))))
    fuel_used = round(actual * random.uniform(0.08, 0.13), 1)
    progress_pct = round(random.uniform(30, 75), 0) if in_progress else 100.0
    ended_at = None if in_progress else when + dt.timedelta(minutes=actual)

    session = {
        "id": _next_session_id(),
        "task_id": task_id,
        "operator_id": operator["id"],
        "machine_id": machine["id"],
        "task_type": task_type,
        "weather": weather,
        "operator_skill": operator["skill_level"],
        "machine_age": machine["age_years"],
        "started_at": when,
        "ended_at": ended_at,
        "estimated_time_min": estimated,
        "actual_time_min": None if in_progress else actual,
        "idle_time_min": idle_time_min if not in_progress else round(idle_time_min * (progress_pct / 100), 1),
        "load_cycles": load_cycles,
        "fuel_used_l": fuel_used,
        "progress_pct": progress_pct,
        "scenario_profile": context or profile,
    }

    events = [
        {"task_session_id": session["id"], "timestamp": when + dt.timedelta(minutes=2), "event_type": "idle_start", "value": None, "event_metadata": None},
        {"task_session_id": session["id"], "timestamp": when + dt.timedelta(minutes=2 + idle_time_min), "event_type": "idle_end", "value": idle_time_min, "event_metadata": context},
        {"task_session_id": session["id"], "timestamp": when + dt.timedelta(minutes=max(3, actual - 5)), "event_type": "cycle_batch", "value": float(load_cycles), "event_metadata": None},
    ]

    safety_events = []
    if random.random() < params["safety_alert_prob"]:
        kind = random.choice(["seatbelt_unfastened", "proximity_warning"])
        triggered_at = when + dt.timedelta(minutes=random.uniform(5, max(6, actual - 5)))
        if kind == "seatbelt_unfastened":
            safety_events.append({
                "operator_id": operator["id"], "machine_id": machine["id"], "task_session_id": session["id"],
                "event_type": "seatbelt_unfastened", "severity": "Warning",
                "message": "Seatbelt unfastened while machine active.",
                "reason": "Operating without a fastened seatbelt increases injury risk during sudden stops or rollover.",
                "recommended_action": "Fasten seatbelt before continuing operation.",
                "source_data": "seatbelt_status=Unfastened, machine_state=Active",
                "triggered_at": triggered_at, "resolved_at": triggered_at + dt.timedelta(minutes=random.uniform(1, 4)),
            })
        else:
            safety_events.append({
                "operator_id": operator["id"], "machine_id": machine["id"], "task_session_id": session["id"],
                "event_type": "proximity_warning", "severity": random.choice(["Caution", "Warning"]),
                "message": "Personnel/equipment detected within hazard proximity.",
                "reason": "Reduced clearance between machine and nearby personnel/equipment raises collision risk.",
                "recommended_action": "Pause travel/swing and confirm the area is clear before continuing.",
                "source_data": "simulated_proximity_distance=2.4m",
                "triggered_at": triggered_at, "resolved_at": triggered_at + dt.timedelta(minutes=random.uniform(1, 6)),
            })

    return session, events, safety_events


def _training_records(operators: list[dict], machines_by_id: dict, today: dt.datetime) -> list[dict]:
    completion_rate = {"Expert": 0.85, "Intermediate": 0.6, "Beginner": 0.35}
    records: list[dict] = []
    for op in operators:
        machine_type = machines_by_id[OPERATOR_MACHINE[op["id"]]]["machine_type"]
        relevant = [c for c in TRAINING_CATALOG if c["machine_family"] in (machine_type, "All")]
        rate = completion_rate[op["skill_level"]]
        for content in relevant:
            if random.random() < rate:
                records.append({
                    "operator_id": op["id"], "training_content_id": content["id"], "status": "Completed",
                    "score": round(random.uniform(72, 99), 1),
                    "completed_at": today - dt.timedelta(days=random.randint(1, HISTORY_DAYS)),
                })
            else:
                records.append({
                    "operator_id": op["id"], "training_content_id": content["id"],
                    "status": random.choice(["Not Started", "In Progress"]), "score": None, "completed_at": None,
                })
    # Demo hook (PRD §10.2 example): beginner operator has a pending trenching refresher.
    records.append({
        "operator_id": "OP1002", "training_content_id": "TRN-video-trenching",
        "status": "Not Started", "score": None, "completed_at": None,
    })
    return records


def _instructor_slots(today: dt.datetime) -> list[dict]:
    slots: list[dict] = []
    for day_offset in range(1, 8):
        day = today + dt.timedelta(days=day_offset)
        for instructor in INSTRUCTORS:
            if random.random() < 0.5:
                continue
            topic = random.choice(instructor["topics"])
            start = day.replace(hour=random.choice([9, 11, 14]), minute=0)
            mode = random.choice(["Virtual", "Onsite"])
            slots.append({
                "instructor_name": instructor["name"], "expertise": instructor["expertise"], "topic": topic,
                "mode": mode, "location": "Site 01 Training Room" if mode == "Onsite" else None,
                "start_time": start, "end_time": start + dt.timedelta(minutes=45),
                "booked_by_operator_id": None,
            })
    if len(slots) > 0:
        slots[0]["booked_by_operator_id"] = "OP1002"
    if len(slots) > 3:
        slots[3]["booked_by_operator_id"] = "OP1004"
    return slots


def _incidents(safety_events: list[dict], task_sessions: list[dict], tasks: list[dict], today: dt.datetime) -> list[dict]:
    session_by_id = {s["id"]: s for s in task_sessions}
    task_by_id = {t["id"]: t for t in tasks}
    category_map = {"seatbelt_unfastened": "Seatbelt", "proximity_warning": "Proximity"}
    description_map = {
        "Seatbelt": "Operator recorded operating with an unfastened seatbelt during {task}; corrected after prompt.",
        "Proximity": "Personnel/equipment detected within hazard proximity during {task}; operator paused swing/travel.",
    }

    candidates = [se for se in safety_events if se["severity"] == "Warning"]
    random.shuffle(candidates)
    chosen = candidates[: min(len(candidates), random.randint(5, 8))]

    incidents: list[dict] = []
    for se in chosen:
        session = session_by_id.get(se["task_session_id"])
        task = task_by_id.get(session["task_id"]) if session else None
        zone = task["zone"] if task else "Zone A"
        category = category_map[se["event_type"]]
        created_at = se["triggered_at"] + dt.timedelta(minutes=random.uniform(1, 10))
        status = "Resolved" if (today - created_at).days > 5 else random.choice(["Reported", "Acknowledged", "Under Investigation"])
        updated_at = created_at if status == "Reported" else created_at + dt.timedelta(hours=random.uniform(1, 48))
        incidents.append({
            "operator_id": se["operator_id"], "machine_id": se["machine_id"],
            "task_id": task["id"] if task else None, "category": category,
            "severity": random.choice(["Low", "Medium", "High"]),
            "description": description_map[category].format(task=session["task_type"] if session else "task operation"),
            "location": zone, "status": status, "photo_url": None,
            "created_at": created_at, "updated_at": updated_at,
        })
    return incidents


def _anomaly_events(task_sessions: list[dict]) -> list[dict]:
    by_key: dict[tuple, list[dict]] = {}
    for s in task_sessions:
        by_key.setdefault((s["operator_id"], s["task_type"]), []).append(s)
    for sessions in by_key.values():
        sessions.sort(key=lambda s: s["started_at"])

    anomalies: list[dict] = []
    for sessions in by_key.values():
        for i, s in enumerate(sessions):
            if s["actual_time_min"] is None:
                continue
            recent = [h for h in sessions[:i] if h["actual_time_min"] is not None][-7:]
            if len(recent) < 3:
                continue
            baseline_idle = median(h["idle_time_min"] for h in recent)
            if baseline_idle <= 0:
                continue
            actual_idle = s["idle_time_min"]
            deviation = round(actual_idle / baseline_idle, 2)
            if deviation < 1.5:
                continue  # idle time isn't meaningfully elevated — not anomaly-card-worthy

            context = s["scenario_profile"] if s["scenario_profile"] in ("excessive_idle", "truck_wait") else None
            status, feedback_reason = "Detected", None
            if context == "truck_wait" and random.random() < 0.6:
                status, feedback_reason = "Confirmed Normal", "Truck arrival delay recorded for this cycle."

            anomalies.append({
                "task_session_id": s["id"], "operator_id": s["operator_id"], "dimension": "idle_time",
                "baseline_value": round(baseline_idle, 1), "actual_value": round(actual_idle, 1),
                "deviation_score": deviation,
                "explanation": (
                    f"Idle time is {deviation}x the recent median for {s['task_type']} "
                    f"({actual_idle:.0f} min vs {baseline_idle:.0f} min typical)."
                ),
                "possible_context": context, "status": status, "feedback_reason": feedback_reason,
                "created_at": s["ended_at"] or s["started_at"],
            })

    random.shuffle(anomalies)
    return anomalies[:10]


def _eta_entry(task_id: str, task_type: str, estimated: float, weather: str, history_count: int,
               predicted_at: dt.datetime) -> dict:
    wf = _weather_factor(weather, task_type)
    point = round(estimated * wf, 1)
    spread = 0.10 if history_count >= 5 else 0.18
    confidence = "High" if history_count >= 5 else ("Medium" if history_count >= 3 else "Low")
    factors = (["Current weather"] if wf != 1.0 else []) + ["Historical cycle duration", "Operator experience"]
    return {
        "task_id": task_id, "point_estimate_min": point,
        "low_estimate_min": round(point * (1 - spread), 1), "high_estimate_min": round(point * (1 + spread), 1),
        "confidence": confidence, "top_factors": json.dumps(factors[:3]), "predicted_at": predicted_at,
    }


def _eta_predictions_and_outcomes(tasks: list[dict], task_sessions: list[dict]) -> tuple[list[dict], list[dict]]:
    sessions_by_op_type: dict[tuple, list[dict]] = {}
    for s in task_sessions:
        sessions_by_op_type.setdefault((s["operator_id"], s["task_type"]), []).append(s)
    session_by_task_id = {s["task_id"]: s for s in task_sessions}

    predictions: list[dict] = []
    outcomes: list[dict] = []

    # Today's not-yet-completed tasks (the ones an operator actually sees an ETA for).
    for task in tasks:
        if task["status"] not in ("Ready", "Not Started", "In Progress"):
            continue
        session = session_by_task_id.get(task["id"])
        weather = session["weather"] if session else "Sunny"
        history_count = len(sessions_by_op_type.get((task["operator_id"], task["task_type"]), []))
        predictions.append(_eta_entry(
            task["id"], task["task_type"], task["estimated_duration_min"], weather, history_count,
            predicted_at=task["planned_start"] - dt.timedelta(minutes=random.uniform(5, 20)),
        ))

    # A sample of completed historical tasks, to demonstrate the predicted-vs-actual feedback loop.
    completed_with_session = [t for t in tasks if t["status"] == "Completed" and t["id"] in session_by_task_id]
    sample = random.sample(completed_with_session, min(10, len(completed_with_session)))
    for task in sample:
        session = session_by_task_id[task["id"]]
        history_count = len(sessions_by_op_type.get((task["operator_id"], task["task_type"]), []))
        entry = _eta_entry(
            task["id"], task["task_type"], task["estimated_duration_min"], session["weather"], history_count,
            predicted_at=session["started_at"] - dt.timedelta(minutes=random.uniform(5, 20)),
        )
        predictions.append(entry)
        outcomes.append({
            "_prediction_index": len(predictions) - 1,  # resolved to a real id at insert time
            "actual_duration_min": session["actual_time_min"],
            "error_min": round(session["actual_time_min"] - entry["point_estimate_min"], 1),
            "recorded_at": session["ended_at"],
        })

    return predictions, outcomes


def generate() -> dict:
    operators = OPERATORS
    machines = MACHINES
    tasks: list[dict] = []
    task_sessions: list[dict] = []
    operation_events: list[dict] = []
    safety_events: list[dict] = []
    environment_snapshots: list[dict] = []

    today = dt.datetime.combine(dt.date.today(), dt.time(6, 0))
    machines_by_id = {m["id"]: m for m in machines}

    # --- historical days (elapsed_days: 0 = HISTORY_DAYS ago, grows toward "now") ---
    for day_idx in range(HISTORY_DAYS, 0, -1):
        day = today - dt.timedelta(days=day_idx)
        weather = random.choice(WEATHER_OPTIONS)
        environment_snapshots.append({
            "site_id": SITE_ID, "timestamp": day, "weather": weather,
            "temperature_c": round(random.uniform(14, 34), 1),
            "wind_kph": round(random.uniform(3, 35), 1),
            "visibility": "Good" if weather != "Rainy" else random.choice(["Good", "Moderate"]),
            "ground_condition": "Wet" if weather == "Rainy" else "Dry",
        })
        elapsed_days = HISTORY_DAYS - day_idx
        for operator in operators:
            machine = machines_by_id[OPERATOR_MACHINE[operator["id"]]]
            num_sessions = random.choice([1, 1, 2])
            start = day + dt.timedelta(hours=random.uniform(1, 3))
            for _ in range(num_sessions):
                task_type = random.choice(TASK_TYPES)
                task_id = f"{operator['id']}-H{len(tasks) + 1:04d}"
                tasks.append({
                    "id": task_id, "operator_id": operator["id"], "machine_id": machine["id"],
                    "site_id": SITE_ID, "zone": random.choice(ZONES), "task_type": task_type,
                    "priority": random.choice(["Low", "Medium", "High"]),
                    "shift_date": start.date(), "planned_start": start,
                    "estimated_duration_min": BASE_DURATION_MIN[task_type],
                    "ai_predicted_duration_min": None, "status": "Completed",
                    "dependencies": None, "required_training": None, "safety_requirements": None,
                })
                session, events, s_events = _make_session(operator, machine, task_id, task_type, start, weather, elapsed_days)
                task_sessions.append(session)
                operation_events.extend(events)
                safety_events.extend(s_events)
                start = (session["ended_at"] or start + dt.timedelta(minutes=session["estimated_time_min"])) + dt.timedelta(minutes=random.uniform(10, 40))

    # --- today: seeded demo storyline (PRD §26 scene 1) ---
    today_weather = "Sunny"
    environment_snapshots.append({
        "site_id": SITE_ID, "timestamp": today, "weather": today_weather,
        "temperature_c": 27.0, "wind_kph": 12.0, "visibility": "Good", "ground_condition": "Dry",
    })

    op1 = operators[0]  # Jordan Reyes, Expert — shift not started yet (Scene 1)
    m1 = machines_by_id[OPERATOR_MACHINE[op1["id"]]]
    demo_tasks = [
        ("Trenching", "High", 8, 0, 56, "Ready", "Pre-operation safety checklist"),
        ("Material Loading", "Medium", 9, 45, 30, "Not Started", None),
        ("Grading", "Medium", 11, 0, 35, "Not Started", None),
        ("Earth Excavation", "Low", 13, 0, 60, "Not Started", None),
    ]
    for i, (task_type, priority, hh, mm, est, status, safety_req) in enumerate(demo_tasks, start=1):
        planned_start = dt.datetime.combine(dt.date.today(), dt.time(hh, mm))
        tasks.append({
            "id": f"{op1['id']}-T{i:03d}", "operator_id": op1["id"], "machine_id": m1["id"],
            "site_id": SITE_ID, "zone": "Zone B", "task_type": task_type, "priority": priority,
            "shift_date": dt.date.today(), "planned_start": planned_start,
            "estimated_duration_min": est, "ai_predicted_duration_min": None, "status": status,
            "dependencies": None, "required_training": None, "safety_requirements": safety_req,
        })

    # OP1002 (beginner) — already mid-task, so Phases 1-2 have a live "current task" to inspect
    op2 = operators[1]
    m2 = machines_by_id[OPERATOR_MACHINE[op2["id"]]]
    in_progress_task_id = f"{op2['id']}-T001"
    started = today.replace(hour=8, minute=0) + dt.timedelta(minutes=40)
    tasks.append({
        "id": in_progress_task_id, "operator_id": op2["id"], "machine_id": m2["id"],
        "site_id": SITE_ID, "zone": "Zone A", "task_type": "Material Loading", "priority": "Medium",
        "shift_date": dt.date.today(), "planned_start": started, "estimated_duration_min": 30,
        "ai_predicted_duration_min": None, "status": "In Progress",
        "dependencies": None, "required_training": None, "safety_requirements": None,
    })
    session, events, s_events = _make_session(op2, m2, in_progress_task_id, "Material Loading", started, today_weather, HISTORY_DAYS, in_progress=True)
    task_sessions.append(session)
    operation_events.extend(events)
    safety_events.extend(s_events)

    # --- derived tables (built from the operational data above, not independently randomized) ---
    training_records = _training_records(operators, machines_by_id, today)
    instructor_slots = _instructor_slots(today)
    incidents = _incidents(safety_events, task_sessions, tasks, today)
    anomaly_events = _anomaly_events(task_sessions)
    eta_predictions, eta_outcomes = _eta_predictions_and_outcomes(tasks, task_sessions)

    return {
        "operators": operators,
        "machines": machines,
        "tasks": tasks,
        "task_sessions": task_sessions,
        "operation_events": operation_events,
        "safety_events": safety_events,
        "environment_snapshots": environment_snapshots,
        "training_content": TRAINING_CATALOG,
        "training_records": training_records,
        "instructor_slots": instructor_slots,
        "incidents": incidents,
        "anomaly_events": anomaly_events,
        "eta_predictions": eta_predictions,
        "eta_outcomes": eta_outcomes,
    }
