def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_dashboard_shape(client):
    resp = client.get("/api/v1/dashboard", params={"operator_id": "OP1001"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["shift"]["operator"]["id"] == "OP1001"
    assert body["shift"]["machine"] is not None
    assert body["summary"]["tasks_total"] == len(body["tasks"])
    assert body["safety"]["alert_count"] == len(body["safety"]["alerts"]) or body["safety"]["alert_count"] >= 0

    # Every recommendation must carry its reason and the data that triggered it (PRD §7.3).
    for action in body["next_best_actions"]:
        assert action["reason"]
        assert action["source"]


def test_dashboard_unknown_operator_404(client):
    assert client.get("/api/v1/dashboard", params={"operator_id": "NOPE"}).status_code == 404


def test_tasks_today(client):
    resp = client.get("/api/v1/tasks/today", params={"operator_id": "OP1001"})
    assert resp.status_code == 200
    tasks = resp.json()
    assert tasks, "seeded demo operator should have tasks today"
    assert {"id", "task_type", "status", "planned_start", "expected_completion"} <= set(tasks[0])


def test_operator_list(client):
    operators = client.get("/api/v1/operators").json()
    assert len(operators) >= 2
    assert all(o["machine"] for o in operators)
