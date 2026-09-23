# Ironsight

An operator-first intelligent work companion for Cat® excavators and loaders: shift dashboard, live jobsite map, safety centre, training hub, hybrid search, explainable anomaly detection, predictive task ETA, and an AI companion that visually guides the operator through the software.

Standalone proof of concept — no real Caterpillar telemetry or systems. All machine, operator, site and environmental data is simulated.

## Stack

| Layer | Choice |
|---|---|
| API | FastAPI + SQLAlchemy 2.0 |
| Database | SQLite (`backend/app.db`) |
| ML | scikit-learn (GradientBoosting ETA, IsolationForest + robust z-score anomalies) |
| Search | TF-IDF (word + char n-gram) + RapidFuzz, in-process |
| LLM | NVIDIA Nemotron via the OpenAI-compatible API, with a deterministic fallback router |
| Live map | asyncio simulation loop + WebSocket broadcast |
| Frontend | *(not built yet)* React + TypeScript + Vite, neumorphic design system |

No Docker, Postgres, Redis or Celery — the whole backend is one process.

## Running the backend

```bash
cd backend
python -m venv .venv                       # use a real Windows CPython, not MSYS2's
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe seed.py         # build app.db from the synthetic dataset
.\.venv\Scripts\python.exe -m app.ml.train_eta   # train the ETA model
.\.venv\Scripts\python.exe -m pytest -q    # 39 tests

.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API docs at http://127.0.0.1:8000/docs.

### Enabling the AI companion

Copy `backend/.env.example` to `backend/.env` and set your key:

```
NVIDIA_API_KEY=nvapi-...
```

Without a key the assistant runs its deterministic keyword router over the same tools, so
every screen still works — the chat just stops being conversational. The same fallback
catches provider errors, timeouts and rate limits at runtime.

## API surface

| Area | Endpoints |
|---|---|
| Dashboard | `GET /api/v1/dashboard` |
| Tasks | `GET /tasks/today`, `GET /tasks/{id}`, `GET /tasks/{id}/eta`, `POST /tasks/{id}/start`, `POST /tasks/{id}/complete`, `PATCH /tasks/{id}/status` |
| Safety | `GET /safety/live`, `/safety/events`, `/safety/timeline`, `/safety/checklist`, `POST /safety/checklists/{task_id}/complete` |
| Incidents | `GET/POST /incidents`, `GET /incidents/{id}`, `PATCH /incidents/{id}/status` |
| Training | `GET /training`, `/training/recommendations`, `/training/search`, `/training/{id}`, `POST /training/{id}/complete`, `GET /instructors/availability`, `POST /training/bookings/{slot_id}` |
| Search | `GET /search`, `POST /search/reindex` |
| Insights | `GET /insights/anomalies`, `/insights/anomalies/{id}`, `POST /insights/anomalies/{id}/feedback`, `GET /insights/baselines`, `/insights/performance` |
| ETA | `POST /eta/predict`, `GET /eta/model`, `/eta/accuracy`, `/eta/tasks/{id}` |
| Assistant | `POST /assistant/message`, `POST /assistant/guide`, `GET /assistant/guide/targets`, `/assistant/status` |
| Live site | `GET /site/map`, `/site/operators`, `/site/hazards`, `/site/events`, `/site/incidents`, `POST /site/reset`, `WS /site/stream` |
| Operators | `GET /operators`, `/operators/{id}` |

## How the intelligence works

**ETA** — GradientBoosting over task type, weather, operator skill, machine age, planned duration and the operator's own rolling median for that task type (computed from prior sessions only, so the target never leaks). Returns a range sized by residual spread and confidence, plus per-prediction factor attribution via counterfactual re-prediction ("Rainy weather: +7.2 min").

**Anomalies** — baselines are scoped to *(operator, task type)*, never global. Robust z-score (median/MAD) identifies which dimension deviated; IsolationForest across idle ratio, duration ratio and fuel-per-cycle adds a multivariate second opinion. Each card carries the actual value, the operator's typical range, the 7-day median, the likely context and the estimated cost in minutes and litres. Operator feedback is stored and closes the loop.

**Safety** — every alert comes from explicit rules over live telemetry and DB history, never from the LLM. Each answers what happened, why it matters, what to do, how long it's been true, and what data triggered it.

**AI guide** — the LLM can only call the registered tools, and can only point at UI elements listed in `services/guide_registry.py`. Actions that operate a control (submit, acknowledge, change threshold, machine control) are not in the registry at all, so there is no path for the model to take them. Every returned plan is validated again before it leaves the API.

## Data

`backend/data_gen/generate.py` builds a correlated 20-day synthetic history plus a seeded "today" storyline: rain slows excavation and trenching, beginners overrun then improve, one operator runs hot on idle time, another accumulates safety alerts. Schema and generation rules are documented in `backend/data_gen/DATASET_SCHEMA.md`.

Re-running `seed.py` rebuilds `app.db` from scratch. Re-run `app.ml.train_eta` afterwards.

## Repo layout

```
backend/
  app/
    main.py          FastAPI app, CORS, lifespan (search index + simulation)
    models.py        14-table SQLAlchemy schema
    schemas.py       Pydantic request validation
    routers/         one module per feature area
    services/        rules, anomaly, eta, search, assistant, guide_registry, simulation
    ml/train_eta.py  offline training -> models/eta_model.joblib
    tests/           39 tests
  data_gen/          synthetic data generator + schema doc
  seed.py
```
