# Dataset Schema — Smart Operator Assistant

Maps 1:1 to `backend/app/models.py`. Each table below is a SQLAlchemy model already defined there; `data_gen/generate.py` now populates every table except `site_state_events` (§15), which is deferred until the Live Site Map screen is actually being built, per the note in that section.

Per PRD §18: the normalized tables here are the source of truth. Do not build one giant flat CSV — the two Problem Statement tables (`Machine Operation Log`, `Task Time Data`) are just denormalized *views* over `task_sessions` + `operation_events` + `safety_events`, produced by a join/export step, not stored separately.

General rules for every table:
- IDs are stable strings matching the pattern already used (`OP10xx`, `EXC00x`/`LDR00x`, `<operator>-T0xx` or `<operator>-H0xxx` for tasks).
- Every row must trace back to one of the **4 fixed operators × 4 fixed machines** already in `generate.py` — don't invent new ones unless the demo narrative needs it.
- Correlate, don't randomize independently (PRD §19): rain slows excavation/trenching/demolition, beginners overrun early and improve over `elapsed_days`, one operator profile runs hot on idle, one racks up safety alerts. Reuse `PROFILE_PARAMS` and `_weather_factor` rather than adding new noise sources.
- Timestamps: `HISTORY_DAYS = 20` days of backdated sessions + one seeded "today" demo storyline (PRD §26). Keep that split.

---

## 1. `operators` — done

| Column | Type | How to generate |
|---|---|---|
| `id` | str PK | `OP100{n}` |
| `name` | str | Fixed roster of 4 |
| `skill_level` | str | Beginner / Intermediate / Expert |
| `experience_years` | float | Consistent with skill_level (Beginner ~1yr, Expert ~9yr) |

Not modeled but implied by the roster: `profile` (scenario profile key, used only inside the generator, not a DB column).

## 2. `machines` — done

| Column | Type | How to generate |
|---|---|---|
| `id` | str PK | `EXC00x` / `LDR00x` |
| `machine_type` | str | Excavator / Loader |
| `model` | str | Cat model number (e.g. `Cat 320`) |
| `age_years` | float | 2–6 |
| `engine_hours` | float | Realistic for age (roughly 500–1000 hrs/yr) |

## 3. `tasks` — done

| Column | Type | How to generate |
|---|---|---|
| `id` | str PK | see ID rule above |
| `operator_id` / `machine_id` | FK | paired via `OPERATOR_MACHINE` |
| `site_id`, `zone` | str | `SITE01`, one of `ZONES` |
| `task_type` | str | one of `TASK_TYPES` |
| `priority` | str | Low/Medium/High |
| `shift_date`, `planned_start` | date/datetime | |
| `estimated_duration_min` | float | from `BASE_DURATION_MIN[task_type]` |
| `ai_predicted_duration_min` | float\|null | leave null at generation time — filled later by the ETA model, not synthetic data |
| `status` | str | Not Started / Ready / In Progress / Blocked / Completed |
| `dependencies` | str\|null | e.g. `"waiting_on:<task_id>"` — only set for the truck-wait scenario |
| `required_training` | str\|null | FK-ish reference to a `training_content.id`, set when task_type needs a refresher |
| `safety_requirements` | str\|null | e.g. `"Pre-operation safety checklist"` |

## 4. `task_sessions` — done

Already fully modeled in `_make_session()`. No changes needed; documented here for completeness since it's the backbone the Problem Statement's two sample tables are exported from.

## 5. `operation_events` — done

Event log per session (`idle_start`, `idle_end`, `cycle_batch`). Fine as-is; extend `event_type` vocabulary only if a new behavioral dimension (PRD §12.2) needs raw evidence to explain an anomaly.

## 6. `safety_events` — done

Covers seatbelt + proximity. No change required for baseline; the 5 additional safety features (§9.2 D–H) don't need their own DB rows unless you want them as first-class alerts — if so, add `event_type` values (`fatigue_risk`, `unsafe_pattern`, `geofence_breach`, `checklist_incomplete`, `environmental_hazard`) reusing this same table rather than adding new ones.

## 7. `environment_snapshots` — done

One row per historical day + one for "today". Fine as-is.

---

## 8. `incidents` — done

One-tap incident log (PRD §9.1-C). Generate a handful (5–8) scattered across the 20 history days, mostly tied to a `safety_events` row that escalated.

| Column | Type | How to generate |
|---|---|---|
| `id` | int PK | autoincrement |
| `operator_id` | FK | pick from the safety event it's tied to, or random |
| `machine_id` | FK\|null | matching operator's machine |
| `task_id` | FK\|null | the task active at that time, if any |
| `category` | str | `Near Miss`, `Proximity`, `Seatbelt`, `Equipment Damage`, `Other` |
| `severity` | str | Low / Medium / High (independent scale from safety_events' alert levels — this is post-hoc incident severity) |
| `description` | str | 1 sentence, human-written style, referencing category+context (e.g. "Personnel entered swing radius during trenching, operator stopped swing.") |
| `location` | str | reuse the task's `zone` |
| `status` | str | Reported → Acknowledged → Under Investigation → Resolved (bias older incidents toward Resolved, recent ones toward Reported) |
| `photo_url` | str\|null | leave null — no real media in POC |
| `created_at` / `updated_at` | datetime | created_at = incident time; updated_at later if status progressed |

---

## 9. `training_content` — done

Static catalog, not per-operator. ~15–20 rows covering all 4 categories from PRD §10.1. This is also what the search feature (§11) indexes, so write real, distinct wording per row (needed for fuzzy/semantic search to look meaningful).

| Column | Type | How to generate |
|---|---|---|
| `id` | str PK | `TRN-video-01`, `TRN-manual-01`, etc. |
| `title` | str | specific, e.g. "Trenching Fundamentals Refresher" |
| `content_type` | str | `video` / `handbook` / `instructor` / `simulation` / `checklist` |
| `machine_family` | str | Excavator / Loader / All |
| `task_type` | str\|null | ties to `TASK_TYPES` where relevant (drives the recommendation engine in §10.2) |
| `skill_level` | str | Beginner / Intermediate / Expert / All |
| `duration_min` | float\|null | 3–45 for video, null for handbook/checklist |
| `body_text` | str | 2–4 sentences of real descriptive content — this is the field search matches against, so include the vocabulary an operator would actually search (e.g. "proximity alert", "bucket angle") |
| `url` | str | placeholder path, e.g. `/training/video/trenching-fundamentals` |

Minimum coverage to build: one safety refresher per task type, one machine handbook per machine family, one quick-reference checklist per task type, 2–3 instructor-led topics, 1–2 simulation scenarios.

## 10. `training_records` — done

Per-operator completion history — feeds the training recommendation engine ("previously completed training") and operator skill narrative.

| Column | Type | How to generate |
|---|---|---|
| `id` | int PK | autoincrement |
| `operator_id` | FK | |
| `training_content_id` | FK | |
| `status` | str | Not Started / In Progress / Completed |
| `score` | float\|null | 60–100 if Completed, null otherwise |
| `completed_at` | datetime\|null | within the 20-day history window |

Give the beginner operator (`OP1002`) fewer completions and a pending trenching refresher (so the §10.2 example recommendation has data to point at). Give the expert (`OP1001`) mostly Completed.

## 11. `instructor_slots` — done

| Column | Type | How to generate |
|---|---|---|
| `id` | int PK | autoincrement |
| `instructor_name` | str | 2–3 fictional names |
| `expertise` | str | Excavator / Loader / Safety |
| `topic` | str | matches a `training_content` topic |
| `mode` | str | Virtual / Onsite |
| `location` | str\|null | site name if Onsite, null if Virtual |
| `start_time` / `end_time` | datetime | future slots relative to "today" (upcoming week), 30–60 min each |
| `booked_by_operator_id` | FK\|null | leave most null (open slots); book 1–2 for demo realism |

## 12. `anomaly_events` — done

This is the explainable-anomaly feature (PRD §12.4). Derive from `task_sessions` you already generated — don't invent new random numbers, compute deviation from the same idle/duration values already in the session.

| Column | Type | How to generate |
|---|---|---|
| `id` | int PK | autoincrement |
| `task_session_id` | FK | the session whose `scenario_profile` is `excessive_idle` or `truck_wait`, or whose `actual_time_min` deviated >20% from `estimated_time_min` |
| `operator_id` | FK | |
| `dimension` | str | `idle_time`, `cycle_duration`, `fuel_per_cycle`, `duration_variance` |
| `baseline_value` | float | median of that operator+task_type's last 7 days for this dimension (compute from the sessions you already generated, don't hardcode) |
| `actual_value` | float | the session's actual value for that dimension |
| `deviation_score` | float | simple ratio or z-score, e.g. `actual/baseline` |
| `explanation` | str | templated sentence like the session's `scenario_profile`/`event_metadata` context, e.g. "Idle time is 2.4x the 7-day median for Trenching." |
| `possible_context` | str\|null | copy from the session's `context` (`truck_wait`, `excessive_idle`) when set |
| `status` | str | Detected / Confirmed Normal / Confirmed Abnormal (leave most as Detected; set 1–2 to Confirmed for demo feedback loop) |
| `feedback_reason` | str\|null | only set when status is Confirmed |
| `created_at` | datetime | session's `ended_at` (or now, if in-progress) |

Only generate anomalies for sessions that already deviate — this table should be small (5–10 rows), not one row per session.

## 13. `eta_predictions` — done

| Column | Type | How to generate |
|---|---|---|
| `id` | int PK | autoincrement |
| `task_id` | FK | tasks with `status` in (In Progress, Ready, Not Started) — completed historical tasks don't need a stored prediction |
| `point_estimate_min` | float | task's `estimated_duration_min` adjusted by weather/operator factors (reuse `_weather_factor`) |
| `low_estimate_min` / `high_estimate_min` | float | point_estimate ± 10–15% |
| `confidence` | str | High / Medium / Low — Low when operator has <3 historical sessions of that task_type |
| `top_factors` | text (JSON list) | e.g. `["Operator experience", "Current weather", "Historical cycle duration"]`, ordered by actual influence used above |
| `predicted_at` | datetime | shortly before task start |

## 14. `eta_outcomes` — done

Only for tasks that both have an `eta_predictions` row **and** are `Completed` with a real `actual_time_min` in their session.

| Column | Type | How to generate |
|---|---|---|
| `id` | int PK | autoincrement |
| `eta_prediction_id` | FK | |
| `actual_duration_min` | float | copy from the matching `task_sessions.actual_time_min` |
| `error_min` | float | `actual_duration_min - point_estimate_min` |
| `recorded_at` | datetime | session's `ended_at` |

---

## 15. Live Site Map data — TODO, not yet in `models.py`

PRD §8.9 requires this for the Live Site Map feature but no table exists yet. If you build that feature, add a `site_state_events` table (append-only) with:

| Column | Type | How to generate |
|---|---|---|
| `id` | int PK | autoincrement |
| `site_id`, `zone_id` | str | reuse `SITE01` / `ZONES` |
| `operator_id`, `machine_id` | FK | |
| `x`, `y` | float | normalized 0–1 map coordinates, walked incrementally per event (small random step, not teleporting) |
| `current_task_id` | FK\|null | |
| `task_status` | str | mirrors `tasks.status` |
| `operating_state` | str | Active / Idle / Blocked / Break / Incident |
| `workload_score` | float | 0–100, derive from queued-task count for that operator |
| `safety_state` | str | Normal / Caution / Warning / Critical — mirror latest `safety_events.severity` if one is open |
| `active_hazard_id` | str\|null | |
| `incident_id` | FK\|null | |
| `event_type` | str | `move`, `state_change`, `hazard_created`, `incident_reported` |
| `timestamp` | datetime | |

This should be generated as a short *replayable script* (a fixed sequence of events for the demo, per PRD §8.8), not bulk-randomized like the history tables — build it only when you're implementing the Live Site Map screen, since PRD §18 explicitly says not to build columns before the feature needs them.

---

## Build order

1. `training_content` (static catalog — no dependencies, needed for both Training Hub and Search).
2. `training_records`, `instructor_slots` (depend on operators + training_content).
3. `incidents` (depends on safety_events/tasks you already have).
4. `anomaly_events` (computed from existing `task_sessions` — write this as a pass over already-generated sessions, not a fresh random generator).
5. `eta_predictions` + `eta_outcomes` (depends on tasks/sessions).
6. `site_state_events` only once the Live Site Map screen is actually being built.

Skipped: a single flat "master CSV" — PRD §18.2 explicitly says not to, and none of the modeled features need it; export a joined view only if some external tool (e.g. a notebook) needs one.
