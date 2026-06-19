"""
Simple web-search RAG.

Flow:
  1. DuckDuckGo text search → top N results (title, snippet, url)
  2. Async-scrape the top pages → extract clean text with BeautifulSoup
  3. Build a context block that gets prepended to the Ollama messages

The heavy DDG call is synchronous, so it runs in a thread via asyncio.to_thread.
Page scraping is async (httpx).
"""

import asyncio
import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_SCRAPE_TIMEOUT = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0)
_SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}

# Tags that carry no useful text
_NOISE_TAGS = [
    "script", "style", "nav", "header", "footer",
    "aside", "form", "noscript", "iframe",
]


def _ddg_search(query: str, max_results: int) -> list[dict[str, Any]]:
    """Synchronous DuckDuckGo search — call via asyncio.to_thread."""
    try:
        from duckduckgo_search import DDGS  # type: ignore[import-untyped]
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception as exc:
        logger.warning("DDG search failed: %s", exc)
        return []


async def _scrape(url: str, client: httpx.AsyncClient, max_chars: int = 1500) -> str:
    """Fetch a page and return clean plain text, truncated to max_chars."""
    try:
        resp = await client.get(url, headers=_SCRAPE_HEADERS, follow_redirects=True)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(_NOISE_TAGS):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:max_chars]
    except Exception as exc:
        logger.debug("Scrape failed for %s: %s", url, exc)
        return ""


async def build_web_context(
    query: str,
    max_results: int = 5,
    scrape_top: int = 3,
) -> str:
    """
    Search the web for `query` and return a formatted context block.
    Returns an empty string if nothing useful is found.
    """
    results: list[dict[str, Any]] = await asyncio.to_thread(
        _ddg_search, query, max_results
    )
    if not results:
        return ""

    # Scrape the top pages in parallel
    async with httpx.AsyncClient(timeout=_SCRAPE_TIMEOUT) as client:
        scrape_tasks = [
            _scrape(r["href"], client)
            for r in results[:scrape_top]
            if r.get("href")
        ]
        scraped = await asyncio.gather(*scrape_tasks)

    lines: list[str] = [
        f"[Web search context — live results fetched right now for: \"{query}\"]",
        "IMPORTANT: The following is real-time data retrieved from the web seconds ago.",
        "Use it to answer the user's question directly. Do NOT say you lack internet",
        "access or cannot check current information — the search was already performed.",
        "---",
    ]

    for i, result in enumerate(results):
        title = result.get("title", "")
        url = result.get("href", "")
        snippet = result.get("body", "")
        page_text = scraped[i] if i < len(scraped) else ""

        lines.append(f"\n## {i + 1}. {title}")
        lines.append(f"Source: {url}")
        # Prefer scraped content over snippet if available and longer
        content = page_text if len(page_text) > len(snippet) else snippet
        if content:
            lines.append(content)

    lines += [
        "\n---",
        "[End of web search context]",
        (
            "Use the information above to answer factual questions "
            "(weather, prices, news, current events, etc.). "
            "If the search results are not relevant to the question, ignore them "
            "and answer from your own knowledge."
        ),
    ]

    return "\n".join(lines)


def inject_context(messages: list[dict], context: str) -> list[dict]:
    """
    Merge web context into the message list.
    If a system message already exists, append the context to it.
    Otherwise prepend a new system message.
    """
    if not context:
        return messages

    if messages and messages[0].get("role") == "system":
        merged = messages[0]["content"] + "\n\n" + context
        return [{"role": "system", "content": merged}] + messages[1:]

    return [{"role": "system", "content": context}] + messages
