async def test_health_returns_ok(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "ollama" in data
    assert "provider" in data
