def test_search_survives_heavy_typos(client):
    """PRD §26 scene 8: 'proxmitiy alert' must still reach the proximity material."""
    body = client.get("/api/v1/search", params={"q": "proxmitiy alrt"}).json()
    assert body["total"] > 0
    blob = " ".join(f"{r['title']} {r['body_text']}" for r in body["results"]).lower()
    assert "proximity" in blob


def test_search_matches_different_wording(client):
    """'how to dig trench safely' should reach trenching safety material (§11)."""
    body = client.get("/api/v1/search", params={"q": "how to dig trench safely"}).json()
    titles = [r["title"].lower() for r in body["results"]]
    assert any("trench" in t for t in titles)


def test_search_returns_quick_answer_and_groups(client):
    body = client.get("/api/v1/search", params={"q": "bucket angle"}).json()
    assert body["quick_answer"]["source_title"]
    assert body["groups"]
    assert all(g["items"] for g in body["groups"])


def test_context_boosts_current_task(client):
    """Same query, different operator context -> different ranking (§11.5)."""
    with_ctx = client.get("/api/v1/search", params={"q": "bucket angle", "operator_id": "OP1001"}).json()
    without = client.get("/api/v1/search", params={"q": "bucket angle", "use_context": False}).json()
    top_with = with_ctx["results"][0]
    assert top_with["score"] >= without["results"][0]["score"]
    assert any(r["context_reasons"] for r in with_ctx["results"])


def test_short_query_does_not_explode(client):
    assert client.get("/api/v1/search", params={"q": "tr"}).status_code == 200
    assert client.get("/api/v1/search", params={"q": " "}).json()["total"] == 0
