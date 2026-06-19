import json
from typing import AsyncGenerator

import httpx

from app.config import settings


async def stream_completion(
    messages: list[dict],
    model_name: str,
) -> AsyncGenerator[str, None]:
    """Yields text deltas. Dispatches to the correct backend based on settings.model_provider."""
    provider = settings.model_provider
    if provider == "ollama":
        async for delta in _stream_ollama(messages, model_name):
            yield delta
    elif provider == "openai":
        async for delta in _stream_openai(messages, model_name):
            yield delta
    elif provider == "anthropic":
        async for delta in _stream_anthropic(messages, model_name):
            yield delta
    elif provider == "openrouter":
        async for delta in _stream_openrouter(messages, model_name):
            yield delta


async def _stream_ollama(
    messages: list[dict], model_name: str
) -> AsyncGenerator[str, None]:
    url = f"{settings.ollama_base_url}/api/chat"
    payload = {"model": model_name, "messages": messages, "stream": True}
    # connect timeout: fail fast if Ollama isn't running
    # read timeout: None = no limit — models can take a long time on first load
    timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if delta := chunk.get("message", {}).get("content", ""):
                    yield delta
                if chunk.get("done"):
                    break


async def _stream_openai(
    messages: list[dict], model_name: str
) -> AsyncGenerator[str, None]:
    # Install: pip install openai
    # Set MODEL_PROVIDER=openai and OPENAI_API_KEY in .env
    raise NotImplementedError("OpenAI provider not yet implemented")
    yield  # make mypy happy with the generator return type


async def _stream_anthropic(
    messages: list[dict], model_name: str
) -> AsyncGenerator[str, None]:
    # Install: pip install anthropic
    # Set MODEL_PROVIDER=anthropic and ANTHROPIC_API_KEY in .env
    raise NotImplementedError("Anthropic provider not yet implemented")
    yield


async def _stream_openrouter(
    messages: list[dict], model_name: str
) -> AsyncGenerator[str, None]:
    # Uses OpenAI-compatible API at https://openrouter.ai/api/v1
    # Set MODEL_PROVIDER=openrouter and OPENROUTER_API_KEY in .env
    raise NotImplementedError("OpenRouter provider not yet implemented")
    yield
