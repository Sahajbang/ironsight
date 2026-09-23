import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.services.simulation import simulation

router = APIRouter(prefix="/api/v1/site", tags=["site"])


@router.get("/map")
def site_map(operator_id: str | None = None, view: str = "supervisor"):
    """Bird's-eye site state. `view=operator` filters to the operator's own zone (PRD §8.10)."""
    return simulation.snapshot(operator_id if view == "operator" else None)


@router.get("/operators")
def site_operators():
    return list(simulation.operators.values())


@router.get("/hazards")
def site_hazards(operator_id: str | None = None):
    return simulation.hazards_for(operator_id) if operator_id else simulation.hazards


@router.get("/events")
def site_events(limit: int = 50):
    return simulation.events[-limit:]


@router.get("/incidents")
def site_incidents(limit: int = 20, db: Session = Depends(get_db)):
    rows = list(db.scalars(select(m.Incident).order_by(m.Incident.created_at.desc()).limit(limit)))
    zones = {op["operator_id"]: op["zone"] for op in simulation.operators.values()}
    return [
        {
            "id": i.id,
            "operator_id": i.operator_id,
            "category": i.category,
            "severity": i.severity,
            "status": i.status,
            "location": i.location,
            "zone": zones.get(i.operator_id, i.location),
            "description": i.description,
            "created_at": i.created_at,
        }
        for i in rows
    ]


@router.post("/reset")
def reset_simulation():
    """Restart the scripted timeline — used to re-run the demo from a known state."""
    simulation.reset()
    return {"reset": True, "tick": simulation.tick_count}


@router.websocket("/stream")
async def stream(websocket: WebSocket):
    await websocket.accept()
    simulation.connect(websocket)
    try:
        await websocket.send_json(_serialized_snapshot())
        while True:
            # The broadcast loop pushes updates; this keeps the socket open and drains pings.
            await asyncio.sleep(30)
            await websocket.send_json({"type": "heartbeat", "tick": simulation.tick_count})
    except WebSocketDisconnect:
        pass
    finally:
        simulation.disconnect(websocket)


def _serialized_snapshot() -> dict:
    from app.services.simulation import _jsonable

    return _jsonable(simulation.snapshot())
