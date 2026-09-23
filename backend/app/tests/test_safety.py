def test_safety_live_alert_contract(client):
    body = client.get("/api/v1/safety/live", params={"operator_id": "OP1001", "persist": False}).json()
    assert "live" in body and "alerts" in body

    # Every alert must answer the five questions from PRD §9.3.
    for alert in body["alerts"]:
        assert alert["message"]
        assert alert["reason"]
        assert alert["recommended_action"]
        assert alert["source_data"]
        assert alert["severity"] in ("Informational", "Caution", "Warning", "Critical")

    severities = [a["severity"] for a in body["alerts"]]
    order = {"Critical": 0, "Warning": 1, "Caution": 2, "Informational": 3}
    assert severities == sorted(severities, key=lambda s: order[s]), "worst alert must come first"


def test_checklist_is_task_and_machine_specific(client):
    tasks = client.get("/api/v1/tasks/today", params={"operator_id": "OP1001"}).json()
    trenching = next(t for t in tasks if t["task_type"] == "Trenching")
    body = client.get("/api/v1/safety/checklist", params={"task_id": trenching["id"]}).json()

    assert "Seatbelt and ROPS condition verified" in body["items"]
    assert any("Utility locates" in item for item in body["items"]), "trenching-specific item expected"
    assert body["completed"] is False


def test_checklist_completion_rejects_partial_then_accepts_full(client):
    tasks = client.get("/api/v1/tasks/today", params={"operator_id": "OP1001"}).json()
    task_id = next(t for t in tasks if t["task_type"] == "Grading")["id"]
    items = client.get("/api/v1/safety/checklist", params={"task_id": task_id}).json()["items"]

    partial = client.post(f"/api/v1/safety/checklists/{task_id}/complete",
                          json={"operator_id": "OP1001", "completed_items": items[:2]})
    assert partial.status_code == 400

    full = client.post(f"/api/v1/safety/checklists/{task_id}/complete",
                       json={"operator_id": "OP1001", "completed_items": items})
    assert full.status_code == 200
    assert full.json()["completed"] is True
    assert client.get("/api/v1/safety/checklist", params={"task_id": task_id}).json()["completed"] is True


def test_safety_timeline_is_chronological(client):
    entries = client.get("/api/v1/safety/timeline", params={"operator_id": "OP1001"}).json()["entries"]
    assert [e["at"] for e in entries] == sorted(e["at"] for e in entries)


def test_incident_lifecycle(client):
    created = client.post("/api/v1/incidents", json={
        "operator_id": "OP1001",
        "category": "Near Miss",
        "severity": "Medium",
        "description": "Ground worker crossed behind the machine during a swing.",
        "location": "Zone B",
    })
    assert created.status_code == 201
    incident = created.json()
    assert incident["status"] == "Reported"
    assert incident["machine_id"], "machine context should be attached automatically"

    updated = client.patch(f"/api/v1/incidents/{incident['id']}/status", json={"status": "Acknowledged"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "Acknowledged"
    assert updated.json()["next_status"] == "Under Investigation"


def test_incident_rejects_bad_category(client):
    resp = client.post("/api/v1/incidents", json={
        "operator_id": "OP1001", "category": "Alien Invasion", "description": "nope", "location": "Zone B",
    })
    assert resp.status_code == 422
