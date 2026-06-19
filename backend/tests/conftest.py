from typing import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def mock_stream():
    """Patches stream_completion so tests never hit real Ollama.

    Both routers imported stream_completion by name, so we patch the reference
    in each router module rather than the original in model_provider.
    """

    async def fake_stream(
        messages: list[dict], model_name: str
    ) -> AsyncGenerator[str, None]:
        for word in ["Hello", " world"]:
            yield word

    with (
        patch("app.routers.chat.stream_completion", new=fake_stream),
        patch("app.routers.code.stream_completion", new=fake_stream),
    ):
        yield
