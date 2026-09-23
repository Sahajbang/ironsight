# Ironsight

### An operator-first intelligence layer for Cat® machines — not another dashboard.

---

## The one-sentence pitch

> **Ironsight turns five disconnected operator tools — task list, safety alerts, training, anomaly detection, time estimation — into one system that understands the operator, explains itself, and can physically walk you to the answer instead of just displaying it.**

---

## The problem, as it actually shows up on a jobsite

An operator's day is scattered across surfaces that don't talk to each other: a paper or app task list, a separate safety checklist, a training portal nobody opens unless forced to, a supervisor's gut feeling about "who's slow today," and a time estimate that's really just a guess carried over from the last job. None of these know about each other. The task list doesn't know the operator is a beginner who's about to hit a task they've never done. The safety system doesn't know a task is running long because of a truck delay, not because the operator is doing something wrong. Nobody explains *why* an alert fired, so operators learn to tune alerts out.

The hackathon brief asks for five capabilities: a task dashboard, safety features, a training hub, unusual-behavior detection, and task-time prediction. **Building five separate widgets that satisfy the checklist is the easy, expected answer — and it's also the wrong product.** Bolted-together features don't create understanding; they create five more screens to check.

---

## The core idea

Instead of five features, Ironsight is **one operator model** — operator × machine × task × environment × shift — that every feature reads from and writes back to. A safety alert, an anomaly, a training recommendation and a time estimate are all just different *views* of the same underlying question:

> **"Given who this operator is, what machine they're on, what task they're doing, and what's happening around them right now — what does that mean, and what should happen next?"**

That reframing is what makes the rest of the product different, not an add-on feature bolted onto a normal dashboard.

---

## What makes this novel (not just "AI-flavored")

| Typical hackathon submission | Ironsight |
|---|---|
| "Is this idle time abnormal?" — a single global threshold | "Is this idle time abnormal **for this operator, on this task, in this weather**?" — a personal, contextual baseline |
| Anomaly detector prints a red flag | Anomaly card explains the deviation, offers a likely cause, and **learns from the operator's own correction** |
| ETA is a single number pulled from a lookup table | ETA is a **range with a confidence level and the named factors that moved it** ("+7 min: rainy weather") |
| AI feature = a chatbot bubble in the corner | AI feature = a **visual guide that moves a pointer to the exact control on screen**, chat is the fallback, not the headline |
| Safety alerts come from the same model that's chatting with you | Safety-critical alerts are **deterministic, rule-based, and never delegated to the LLM** — the AI explains, it never decides |
| Generic SaaS dashboard skin, maybe purple gradients | Purpose-built **industrial instrumentation look** — no generic "AI product" aesthetic |

---

## Walking through the five required capabilities — the way we actually built them

### 1. Daily task dashboard
Not a static list sorted by time. It surfaces a **Next Best Action** — "Training refresher recommended before this task," "Weather may add 10 minutes to trenching" — with the reason attached, so the operator understands *why* something is being suggested, not just that it is.

### 2. Safety features
Seatbelt compliance, proximity hazards and incident logging are the floor, not the ceiling — we added fatigue/distraction risk, unsafe-pattern detection, geofence awareness, a dynamic pre-op checklist, and environmental hazard awareness. Every alert answers five questions by construction: *what happened, why it matters, what to do, how long it's been true, and what data triggered it.* And critically: **none of this depends on the LLM being right.** Alerts are deterministic rules over telemetry; the AI's job is to explain them in plain language, not generate them.

### 3. Operator training hub
Training isn't a portal you have to remember to visit — it's recommended *because* of what just happened: two trenching cycles that ran long triggers a 4-minute refresher suggestion, with the trigger shown, not hidden.

### 4. Unusual-behavior detection — the differentiator
We call this the **Operator Behavior Fingerprint**. Instead of one global "normal," every operator gets their own baseline per task type, built from their own history. 60 minutes idle during excavation might be a red flag for one operator and completely normal for another who's waiting on a truck delivery — the system knows the difference because it's comparing against *that operator's* pattern, not an arbitrary company-wide number. Every flagged anomaly comes with an explanation card (typical range, recent median, likely cause, estimated cost in minutes/fuel) and a feedback loop — when an operator says "this was normal, a truck was late," the system remembers that context for next time. That's what turns a static ML model into a system that actually learns from the people using it.

### 5. Task time estimation
Never a single black-box number. Always a range, a confidence level, and the two or three factors that moved the estimate away from baseline — so an operator (or a supervisor) can see *why* today's estimate is longer than usual, not just that it is.

---

## The signature feature: an AI that shows you, not just tells you

Most hackathon "AI features" are a chat window bolted onto the side of an app. Ours is built around the opposite idea: **the AI's primary interface is a pointer, not a paragraph.**

Ask "How do I report this?" and instead of a wall of text, a guide pointer physically travels across the screen to the *Report Incident* button, highlights it, and says "Select this." The AI is restricted to a fixed registry of real UI elements and a small set of safe actions (navigate, highlight, explain) — it cannot invent a button that doesn't exist, and it cannot submit, acknowledge, or change anything on the operator's behalf. Chat is still there as a fallback, but the pointer is the feature people remember.

---

## Why this framing wins on the judging criteria

- **Innovation:** the personal-baseline anomaly engine and the pointer-based AI guide are both genuinely uncommon patterns, not a rebrand of a standard dashboard.
- **Feasibility:** this isn't a concept sketch — the backend, ML models, search, rule-based safety engine and AI guide are already built and running end-to-end against a realistic, correlated synthetic dataset (rain slows tasks, beginners overrun and improve, one operator runs hot on idle time, one accumulates safety alerts).
- **Impact:** it directly reduces the two costs that matter most on a jobsite — safety incidents and wasted time — and it does so by explaining itself, which is what actually earns operator trust and adoption, unlike a system that just issues warnings.
- **Design:** an industrial, instrumentation-inspired visual language instead of a templated SaaS/AI look, because this is a tool for a cab, not a boardroom.

---

## The demo story, in one breath

*Operator starts a shift → sees today's tasks and a recommended next action → begins trenching → gets a live ETA range with the reason it's longer than usual (rain) → an idle-time anomaly appears, explained against their own baseline, not a generic threshold → they confirm it was a truck delay, and the system remembers that → a proximity alert fires from deterministic safety rules → they ask "how do I log this?" and the AI pointer walks them straight to the incident form → the task finishes, predicted vs. actual is logged, and the model gets a little better for next time.*

That loop — see, act, understand, get help, improve — is the product. The five checklist features are just where that loop touches the screen.
