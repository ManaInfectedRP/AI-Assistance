import json


async def test_chat_streams_sse(client, mock_stream):
    body = {"messages": [{"role": "user", "content": "hi"}], "stream": True}
    async with client.stream("POST", "/api/chat", json=body) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        lines = []
        async for line in r.aiter_lines():
            if line.startswith("data:"):
                lines.append(line)
    assert len(lines) >= 1
    last = json.loads(lines[-1].removeprefix("data: "))
    assert last["done"] is True


async def test_code_streams_sse(client, mock_stream):
    body = {"messages": [{"role": "user", "content": "write hello world"}], "stream": True}
    async with client.stream("POST", "/api/code", json=body) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        lines = [
            line async for line in r.aiter_lines() if line.startswith("data:")
        ]
    assert len(lines) >= 1
