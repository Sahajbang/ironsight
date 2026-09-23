"""AI Companion: guide-plan validation and the deterministic fallback path.

The Nemotron call itself is not exercised here — these tests must pass with no API key and
no network, which is also the guarantee that the product degrades gracefully (PRD §23).
"""
from app.services import guide_registry


def test_restricted_actions_are_dropped():
    plan = guide_registry.validate_actions([
        {"action": "highlight", "target": "report-incident", "message": "Here"},
        {"action": "submit", "target": "report-incident", "message": "Send it"},
        {"action": "click", "target": "report-incident", "message": "Click"},
        {"action": "machine_control", "target": "report-incident", "message": "Swing"},
    ])
    assert len(plan) == 1
    assert plan[0]["action"] == "highlight"


def test_unknown_targets_are_dropped():
    assert guide_registry.validate_actions(
        [{"action": "highlight", "target": "definitely-not-real", "message": "x"}]
    ) == []


def test_guide_plan_navigates_then_highlights():
    plan = guide_registry.plan_for_target("report-incident", "Select Report Incident.")
    assert [step["action"] for step in plan] == ["navigate", "scroll", "highlight"]
    assert plan[0]["route"] == "/incidents"
    assert plan[-1]["waitForUser"] is True


def test_assistant_guides_to_incident_workflow(client):
    """PRD §14.2: 'I don't know how to report this safety issue' -> pointer on Report Incident."""
    body = client.post("/api/v1/assistant/message", json={
        "message": "I don't know how to report this safety issue",
        "operator_id": "OP1001",
        "route": "/",
    }).json()

    assert body["reply"]
    targets = {step["target"] for step in body["guide_actions"]}
    assert "report-incident" in targets
    # Whatever produced the plan, it must never contain an action that operates a control.
    assert all(step["action"] in guide_registry.ALLOWED_ACTIONS for step in body["guide_actions"])


def test_assistant_answers_eta_question_with_real_numbers(client):
    body = client.post("/api/v1/assistant/message", json={
        "message": "how long until I finish?", "operator_id": "OP1001",
    }).json()
    assert body["reply"]
    assert body["source"] in ("nemotron", "fallback")


def test_assistant_status_reports_llm_configuration(client):
    body = client.get("/api/v1/assistant/status").json()
    assert "llm_configured" in body
    assert body["provider"] == "nvidia-nemotron"


def test_guide_targets_endpoint_lists_registry(client):
    body = client.get("/api/v1/assistant/guide/targets").json()
    ids = {t["id"] for t in body["targets"]}
    assert {"report-incident", "start-checklist", "site-map"} <= ids
    assert "submit" in body["restricted_actions"]
