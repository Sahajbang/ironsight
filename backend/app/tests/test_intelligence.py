"""ETA prediction, anomaly detection and the predicted-vs-actual loop."""


def test_eta_returns_range_not_a_number(client):
    body = client.post("/api/v1/eta/predict", json={
        "task_type": "Trenching", "estimated_duration_min": 56, "weather": "Sunny",
        "operator_skill": "Expert", "machine_age": 2, "operator_id": "OP1001",
    }).json()

    assert body["low_estimate_min"] < body["point_estimate_min"] < body["high_estimate_min"]
    assert body["confidence"] in ("High", "Medium", "Low")
    assert body["top_factors"], "an ETA without contributing factors is a black box"
    for factor in body["top_factors"]:
        assert factor["name"] and factor["direction"] in ("increase", "decrease")


def test_rain_pushes_excavation_eta_out(client):
    sunny = client.post("/api/v1/eta/predict", json={
        "task_type": "Earth Excavation", "estimated_duration_min": 60, "weather": "Sunny",
        "operator_skill": "Intermediate", "machine_age": 3,
    }).json()
    rainy = client.post("/api/v1/eta/predict", json={
        "task_type": "Earth Excavation", "estimated_duration_min": 60, "weather": "Rainy",
        "operator_skill": "Intermediate", "machine_age": 3,
    }).json()
    assert rainy["point_estimate_min"] > sunny["point_estimate_min"]


def test_eta_model_is_trained(client):
    info = client.get("/api/v1/eta/model").json()
    assert info["trained"] is True, "run `python -m app.ml.train_eta` after seeding"
    assert info["metrics"]["mae"] > 0


def test_anomaly_cards_explain_themselves(client):
    anomalies = client.get("/api/v1/insights/anomalies", params={"operator_id": "OP1003"}).json()
    assert anomalies, "OP1003 is the excessive-idle profile and should have anomalies"
    for row in anomalies:
        assert row["explanation"]
        assert row["actual_value"] > row["baseline_value"]
        assert row["deviation_score"] >= 1.0


def test_anomaly_detail_includes_baseline_and_timeline(client):
    anomaly_id = client.get("/api/v1/insights/anomalies", params={"operator_id": "OP1003"}).json()[0]["id"]
    detail = client.get(f"/api/v1/insights/anomalies/{anomaly_id}").json()
    assert detail["baselines"]["sample_count"] >= 3
    assert "timeline" in detail


def test_anomaly_feedback_closes_the_learning_loop(client):
    anomaly_id = client.get("/api/v1/insights/anomalies", params={"operator_id": "OP1003"}).json()[0]["id"]
    updated = client.post(f"/api/v1/insights/anomalies/{anomaly_id}/feedback",
                          json={"status": "Confirmed Normal", "reason": "Truck arrival delay."}).json()
    assert updated["status"] == "Confirmed Normal"
    assert updated["feedback_reason"] == "Truck arrival delay."


def test_start_then_complete_task_records_eta_outcome(client):
    tasks = client.get("/api/v1/tasks/today", params={"operator_id": "OP1001"}).json()
    task_id = next(t for t in tasks if t["status"] in ("Ready", "Not Started"))["id"]

    started = client.post(f"/api/v1/tasks/{task_id}/start")
    assert started.status_code == 200
    assert started.json()["task"]["status"] == "In Progress"

    completed = client.post(f"/api/v1/tasks/{task_id}/complete", json={"actual_time_min": 61.0})
    assert completed.status_code == 200
    outcome = completed.json()["eta_outcome"]
    assert outcome["actual_min"] == 61.0
    assert outcome["error_min"] == round(61.0 - outcome["predicted_min"], 1)

    accuracy = client.get("/api/v1/eta/accuracy").json()
    assert accuracy["scored"] >= 1
    assert accuracy["mae_min"] is not None


def test_performance_rollup(client):
    body = client.get("/api/v1/insights/performance", params={"operator_id": "OP1001"}).json()
    assert body["sessions"] >= 0
    assert "eta_accuracy" in body
