from data_gen.generate import generate


def test_generate_produces_consistent_dataset():
    data = generate()

    assert len(data["operators"]) == 4
    assert len(data["training_content"]) >= 15

    session_ids = {s["id"] for s in data["task_sessions"]}
    task_ids = {t["id"] for t in data["tasks"]}

    # Every anomaly card must reflect a genuinely elevated idle time (regression check:
    # anomalies were previously selected by an unrelated duration-deviation proxy, which
    # let sessions with *below-baseline* idle time through as false "anomalies").
    for anomaly in data["anomaly_events"]:
        assert anomaly["task_session_id"] in session_ids
        assert anomaly["deviation_score"] >= 1.5
        assert anomaly["actual_value"] > anomaly["baseline_value"]

    # Every eta_outcome must resolve to a real prediction in the same batch.
    for outcome in data["eta_outcomes"]:
        assert 0 <= outcome["_prediction_index"] < len(data["eta_predictions"])

    for incident in data["incidents"]:
        if incident["task_id"] is not None:
            assert incident["task_id"] in task_ids
