from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import NVIDIA_API_KEY, NVIDIA_MODEL
from app.db import Base, SessionLocal, engine
from app.routers import (
    assistant, dashboard, eta, incidents, insights, operators, safety, search, site, tasks, training,
)
from app.services.search import index as search_index
from app.services.simulation import simulation

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db = SessionLocal()
    try:
        search_index.build(db)
    finally:
        db.close()
    await simulation.start()
    yield
    await simulation.stop()


app = FastAPI(title="Ironsight API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (dashboard, tasks, safety, incidents, training, search, insights, eta, assistant, site, operators):
    app.include_router(module.router)


@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "simulation_tick": simulation.tick_count,
        "llm_configured": bool(NVIDIA_API_KEY),
        "llm_model": NVIDIA_MODEL if NVIDIA_API_KEY else None,
    }
