def test_site_map_snapshot(client):
    body = client.get("/api/v1/site/map").json()
    assert body["zones"], "stylized site layout should be part of the payload"
    assert body["operators"], "roster should be loaded from the seeded DB"
    for op in body["operators"]:
        assert 0 <= op["x"] <= 1 and 0 <= op["y"] <= 1, "coordinates are normalized for the map"
        assert op["operating_state"] in ("Active", "Idle", "Blocked", "Break", "Incident")


def test_operator_view_is_scoped(client):
    supervisor = client.get("/api/v1/site/map").json()
    operator = client.get("/api/v1/site/map", params={"operator_id": "OP1001", "view": "operator"}).json()
    assert len(operator["operators"]) <= len(supervisor["operators"])
    assert any(o["operator_id"] == "OP1001" for o in operator["operators"])


def test_simulation_advances(client):
    from app.services.simulation import simulation

    before = simulation.tick_count
    simulation.tick()
    assert simulation.tick_count == before + 1


def test_training_catalog_and_progress(client):
    body = client.get("/api/v1/training", params={"operator_id": "OP1002"}).json()
    assert body["total"] >= 15
    types = {c["content_type"] for c in body["categories"] and body["items"]}
    assert {"video", "handbook", "instructor", "simulation"} <= types
    assert sum(body["progress"].values()) == body["total"]


def test_training_recommendations_explain_their_trigger(client):
    recs = client.get("/api/v1/training/recommendations", params={"operator_id": "OP1002"}).json()
    assert recs, "the beginner operator should get recommendations"
    for rec in recs:
        assert rec["reason"], "PRD §10.2: recommendations must explain their trigger"
        assert rec["trigger"]


def test_instructor_booking(client):
    slots = client.get("/api/v1/instructors/availability").json()
    open_slot = next(s for s in slots if not s["booked"])
    booked = client.post(f"/api/v1/training/bookings/{open_slot['id']}", json={"operator_id": "OP1001"})
    assert booked.status_code == 200
    assert booked.json()["booked_by_operator_id"] == "OP1001"

    again = client.post(f"/api/v1/training/bookings/{open_slot['id']}", json={"operator_id": "OP1003"})
    assert again.status_code == 409


def test_training_completion_updates_record(client):
    done = client.post("/api/v1/training/TRN-video-trenching/complete", json={"operator_id": "OP1002"})
    assert done.status_code == 200
    assert done.json()["status"] == "Completed"
