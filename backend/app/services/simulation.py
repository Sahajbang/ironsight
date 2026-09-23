"""In-memory jobsite simulation (PRD §8.8).

Owns the *live* state the rest of the app treats as telemetry: where each operator is,
what they're doing, seatbelt/proximity readings, and active hazards. Deterministic by
default (fixed seed + a scripted event timeline) so a demo replays identically; the same
loop also drives randomized drift for visual validation.

ponytail: single in-process loop with a full-snapshot broadcast. Fine for 4 operators;
if this ever needs many sites or many clients, move to Redis pub/sub + diffed payloads.
"""
import asyncio
import datetime as dt
import random
from typing import Any

from sqlalchemy import select

from app import models as m
from app.db import SessionLocal

TICK_SECONDS = 2.0
SCRIPT_LENGTH = 60  # scripted timeline repeats every 60 ticks (~2 min)
MAX_EVENTS = 200

ZONES = {
    "Zone A": {"label": "Excavation Zone", "x": 0.05, "y": 0.10, "w": 0.30, "h": 0.35, "kind": "excavation"},
    "Zone B": {"label": "Active Work Zone", "x": 0.40, "y": 0.08, "w": 0.30, "h": 0.30, "kind": "active"},
    "Zone C": {"label": "Loading Zone", "x": 0.05, "y": 0.55, "w": 0.25, "h": 0.35, "kind": "loading"},
    "Zone D": {"label": "Material Storage", "x": 0.45, "y": 0.55, "w": 0.25, "h": 0.30, "kind": "storage"},
    "Restricted": {"label": "Restricted Area", "x": 0.76, "y": 0.15, "w": 0.19, "h": 0.30, "kind": "restricted"},
    "Parking": {"label": "Equipment Parking", "x": 0.76, "y": 0.60, "w": 0.19, "h": 0.30, "kind": "parking"},
}

HAUL_ROUTE = [(0.20, 0.48), (0.38, 0.50), (0.58, 0.50), (0.78, 0.52)]

OPERATING_STATES = ["Active", "Idle", "Blocked", "Break", "Incident"]


def _zone_centre(zone: str) -> tuple[float, float]:
    z = ZONES.get(zone, ZONES["Zone A"])
    return z["x"] + z["w"] / 2, z["y"] + z["h"] / 2


def _clamp_to_zone(zone: str, x: float, y: float) -> tuple[float, float]:
    z = ZONES.get(zone, ZONES["Zone A"])
    return (
        min(max(x, z["x"] + 0.02), z["x"] + z["w"] - 0.02),
        min(max(y, z["y"] + 0.02), z["y"] + z["h"] - 0.02),
    )


class SiteSimulation:
    def __init__(self) -> None:
        self.rng = random.Random(7)
        self.tick_count = 0
        self.site_id = "SITE01"
        self.operators: dict[str, dict[str, Any]] = {}
        self.hazards: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self._clients: set[Any] = set()
        self._task: asyncio.Task | None = None
        self._hazard_seq = 0

    # ---------- lifecycle ----------

    def load_roster(self) -> None:
        """Seed live state from the DB roster (operators, their machine and today's task)."""
        db = SessionLocal()
        try:
            operators = list(db.scalars(select(m.Operator).order_by(m.Operator.id)))
            zones = ["Zone B", "Zone C", "Zone A", "Zone D"]
            for i, op in enumerate(operators):
                task = db.scalars(
                    select(m.Task)
                    .where(m.Task.operator_id == op.id, m.Task.shift_date == dt.date.today())
                    .order_by(m.Task.planned_start)
                ).first()
                zone = task.zone if task and task.zone in ZONES else zones[i % len(zones)]
                cx, cy = _zone_centre(zone)
                self.operators[op.id] = {
                    "operator_id": op.id,
                    "operator_name": op.name,
                    "machine_id": task.machine_id if task else None,
                    "machine_type": None,
                    "zone": zone,
                    "x": round(cx + self.rng.uniform(-0.04, 0.04), 4),
                    "y": round(cy + self.rng.uniform(-0.04, 0.04), 4),
                    "heading": self.rng.uniform(0, 360),
                    "current_task_id": task.id if task else None,
                    "task_status": task.status if task else "Not Started",
                    "operating_state": "Active" if task and task.status == "In Progress" else "Idle",
                    "workload_score": 40.0 + i * 12,
                    "safety_state": "Normal",
                    "seatbelt_status": "Fastened",
                    "proximity_distance_m": 12.0,
                    "engine_on": True,
                    "active_hazard_id": None,
                    "last_event_timestamp": dt.datetime.now(),
                    "event_type": "roster_loaded",
                }
                if task:
                    machine = db.get(m.Machine, task.machine_id)
                    if machine:
                        self.operators[op.id]["machine_type"] = machine.machine_type
        finally:
            db.close()

    async def start(self) -> None:
        if not self.operators:
            self.load_roster()
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        try:
            while True:
                await asyncio.sleep(TICK_SECONDS)
                self.tick()
                await self.broadcast()
        except asyncio.CancelledError:
            pass

    def reset(self) -> None:
        self.rng = random.Random(7)
        self.tick_count = 0
        self.hazards.clear()
        self.events.clear()
        self.operators.clear()
        self._hazard_seq = 0
        self.load_roster()

    # ---------- simulation ----------

    def tick(self) -> None:
        self.tick_count += 1
        for state in self.operators.values():
            self._drift(state)
        self._run_script()
        self._expire_hazards()

    def _drift(self, state: dict[str, Any]) -> None:
        if state["operating_state"] in ("Active", "Blocked"):
            x = state["x"] + self.rng.uniform(-0.012, 0.012)
            y = state["y"] + self.rng.uniform(-0.012, 0.012)
            state["x"], state["y"] = (round(v, 4) for v in _clamp_to_zone(state["zone"], x, y))
            state["heading"] = round((state["heading"] + self.rng.uniform(-25, 25)) % 360, 1)

        if state["operating_state"] == "Active":
            state["workload_score"] = min(100.0, round(state["workload_score"] + self.rng.uniform(-1.5, 2.0), 1))
        elif state["operating_state"] == "Idle":
            state["workload_score"] = max(0.0, round(state["workload_score"] - self.rng.uniform(0, 1.5), 1))

        # proximity reading drifts; hazard generation is handled by the script/threshold below
        state["proximity_distance_m"] = round(max(0.8, state["proximity_distance_m"] + self.rng.uniform(-1.2, 1.2)), 1)
        if state["proximity_distance_m"] < 3.0 and state["active_hazard_id"] is None:
            self._create_hazard(state, "proximity", "Warning", "Personnel detected within 3 m of machine envelope.")

    def _run_script(self) -> None:
        """Deterministic demo beats (PRD §8.8 event chain), repeating every SCRIPT_LENGTH ticks."""
        beat = self.tick_count % SCRIPT_LENGTH
        ids = list(self.operators)
        if not ids:
            return

        if beat == 5 and len(ids) > 2:
            self._set_state(ids[2], "Idle", "Idle period began — no active work detected.")
        elif beat == 12 and len(ids) > 1:
            self.operators[ids[1]]["workload_score"] = 88.0
            self._emit(ids[1], "workload_change", "Workload elevated — multiple queued tasks.")
        elif beat == 18:
            self._create_hazard(self.operators[ids[0]], "proximity", "Warning",
                                "Ground personnel entered swing radius near active trenching.")
        elif beat == 26 and len(ids) > 3:
            self.operators[ids[3]]["seatbelt_status"] = "Unfastened"
            self.operators[ids[3]]["safety_state"] = "Warning"
            self._emit(ids[3], "seatbelt_change", "Seatbelt unfastened while machine active.")
        elif beat == 34 and len(ids) > 3:
            self.operators[ids[3]]["seatbelt_status"] = "Fastened"
            self.operators[ids[3]]["safety_state"] = "Normal"
            self._emit(ids[3], "seatbelt_change", "Seatbelt refastened.")
        elif beat == 40 and len(ids) > 2:
            self._set_state(ids[2], "Active", "Work resumed after idle period.")
        elif beat == 46 and len(ids) > 1:
            self._set_state(ids[1], "Blocked", "Task blocked — waiting on haul truck.")
        elif beat == 54 and len(ids) > 1:
            self._set_state(ids[1], "Active", "Haul truck arrived — task resumed.")

    def _set_state(self, operator_id: str, operating_state: str, message: str) -> None:
        state = self.operators.get(operator_id)
        if not state:
            return
        state["operating_state"] = operating_state
        self._emit(operator_id, "state_change", message)

    def _create_hazard(self, state: dict[str, Any], kind: str, severity: str, message: str) -> None:
        self._hazard_seq += 1
        hazard_id = f"HZ-{self._hazard_seq:03d}"
        hazard = {
            "id": hazard_id,
            "hazard_type": kind,
            "severity": severity,
            "zone": state["zone"],
            "x": state["x"],
            "y": state["y"],
            "message": message,
            "source": "simulation",
            "created_at": dt.datetime.now(),
            "expires_tick": self.tick_count + 12,
            "status": "Active",
            "affected_operators": [state["operator_id"]],
        }
        self.hazards.append(hazard)
        state["active_hazard_id"] = hazard_id
        state["safety_state"] = severity
        self._emit(state["operator_id"], "hazard_created", message, hazard_id=hazard_id)

    def _expire_hazards(self) -> None:
        still_active = []
        for hazard in self.hazards:
            if self.tick_count >= hazard["expires_tick"]:
                hazard["status"] = "Cleared"
                for op_id in hazard["affected_operators"]:
                    state = self.operators.get(op_id)
                    if state and state["active_hazard_id"] == hazard["id"]:
                        state["active_hazard_id"] = None
                        state["safety_state"] = "Normal"
                        state["proximity_distance_m"] = 12.0
                self._emit(hazard["affected_operators"][0], "hazard_cleared",
                           f"Hazard {hazard['id']} cleared.", hazard_id=hazard["id"])
            else:
                still_active.append(hazard)
        self.hazards = still_active

    def _emit(self, operator_id: str, event_type: str, message: str, hazard_id: str | None = None) -> None:
        state = self.operators.get(operator_id, {})
        event = {
            "tick": self.tick_count,
            "timestamp": dt.datetime.now(),
            "operator_id": operator_id,
            "zone": state.get("zone"),
            "event_type": event_type,
            "message": message,
            "hazard_id": hazard_id,
        }
        state["last_event_timestamp"] = event["timestamp"]
        state["event_type"] = event_type
        self.events.append(event)
        del self.events[:-MAX_EVENTS]

    def emit(self, operator_id: str, event_type: str, message: str, hazard_id: str | None = None) -> None:
        """Public hook for the rest of the app to push a real event onto the site timeline."""
        self._emit(operator_id, event_type, message, hazard_id)

    # ---------- reads ----------

    def operator_state(self, operator_id: str) -> dict[str, Any]:
        if operator_id not in self.operators and not self.operators:
            self.load_roster()
        return self.operators.get(operator_id, {})

    def machine_state(self, operator_id: str) -> dict[str, Any]:
        state = self.operator_state(operator_id)
        return {
            "machine_id": state.get("machine_id"),
            "seatbelt_status": state.get("seatbelt_status", "Unknown"),
            "proximity_distance_m": state.get("proximity_distance_m"),
            "engine_on": state.get("engine_on", False),
            "operating_state": state.get("operating_state", "Unknown"),
            "zone": state.get("zone"),
            "safety_state": state.get("safety_state", "Normal"),
        }

    def hazards_for(self, operator_id: str) -> list[dict[str, Any]]:
        return [h for h in self.hazards if operator_id in h["affected_operators"]]

    def snapshot(self, operator_id: str | None = None) -> dict[str, Any]:
        if not self.operators:
            self.load_roster()
        operators = list(self.operators.values())
        if operator_id:
            # Operator view: self plus anyone sharing the zone (PRD §8.10)
            own = self.operators.get(operator_id)
            if own:
                operators = [o for o in operators if o["operator_id"] == operator_id or o["zone"] == own["zone"]]
        return {
            "site_id": self.site_id,
            "tick": self.tick_count,
            "generated_at": dt.datetime.now(),
            "zones": [{"id": zid, **z} for zid, z in ZONES.items()],
            "haul_route": HAUL_ROUTE,
            "operators": operators,
            "hazards": self.hazards,
            "recent_events": self.events[-25:],
        }

    # ---------- websocket fan-out ----------

    def connect(self, websocket: Any) -> None:
        self._clients.add(websocket)

    def disconnect(self, websocket: Any) -> None:
        self._clients.discard(websocket)

    async def broadcast(self) -> None:
        if not self._clients:
            return
        payload = _jsonable(self.snapshot())
        dead = []
        for ws in list(self._clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


simulation = SiteSimulation()
