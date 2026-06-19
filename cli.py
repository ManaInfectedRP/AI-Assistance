#!/usr/bin/env python
"""
AI Assistant CLI — terminal chat powered by local Ollama models.

Usage:
    python cli.py                     # chat mode (qwen3)
    python cli.py --model code        # code mode (qwen3-coder)
    python cli.py --project Fantasy-Quest  # load project knowledge

Commands (type during chat):
    /web        toggle web search on/off
    /project <name>   load a project's AI-Knowledge docs (or 'none')
    /model      toggle between chat and code model
    /clear      clear conversation history
    /help       show this list
    /exit       quit
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# ── Try to import optional dependencies with a helpful error ──────────────────
try:
    import httpx
except ImportError:
    sys.exit("httpx not found — run: pip install httpx")

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.theme import Theme
    from rich import print as rprint
except ImportError:
    sys.exit("rich not found — run: pip install rich")

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_URL    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL    = os.getenv("CHAT_MODEL",  "qwen3")
CODE_MODEL    = os.getenv("CODE_MODEL",  "qwen3-coder")
PROJECTS_ROOT = Path(os.getenv("PROJECTS_ROOT", r"C:\Users\quo\repos"))

THEME = Theme({
    "user":      "bold cyan",
    "assistant": "bold green",
    "system":    "dim yellow",
    "error":     "bold red",
    "info":      "dim white",
    "accent":    "bold magenta",
})

console = Console(theme=THEME, highlight=False)

# ── Ollama streaming ──────────────────────────────────────────────────────────
async def stream_ollama(messages: list[dict], model: str):
    """Yield text deltas from Ollama /api/chat streaming endpoint."""
    url = f"{OLLAMA_URL}/api/chat"
    payload = {"model": model, "messages": messages, "stream": True}
    timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=payload) as resp:
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama returned HTTP {resp.status_code}")
            async for line in resp.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if delta := chunk.get("message", {}).get("content", ""):
                    yield delta
                if chunk.get("done"):
                    break

# ── Web search ────────────────────────────────────────────────────────────────
def _ddg_search(query: str, max_results: int = 5) -> list[dict]:
    import time as _time
    delays = [1.5, 3.0, 6.0]
    for attempt, delay in enumerate(delays):
        try:
            from duckduckgo_search import DDGS  # type: ignore
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as exc:
            exc_str = str(exc).lower()
            is_rate = "ratelimit" in exc_str or "202" in exc_str
            if attempt == len(delays) - 1:
                console.print(f"[error]Web search failed: {exc}[/error]")
                return []
            label = "Rate-limited" if is_rate else "Search error"
            console.print(f"[info]{label}, retrying in {delay:.0f}s…[/info]")
            _time.sleep(delay)
    return []


async def _scrape(url: str, client: httpx.AsyncClient, max_chars: int = 1500) -> str:
    try:
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = await client.get(url, headers=headers, follow_redirects=True,
                                timeout=httpx.Timeout(connect=5.0, read=8.0))
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        return " ".join(soup.get_text(separator=" ").split())[:max_chars]
    except Exception:
        return ""


async def build_web_context(query: str) -> str:
    results = await asyncio.to_thread(_ddg_search, query)
    if not results:
        return ""
    async with httpx.AsyncClient() as client:
        scraped = await asyncio.gather(*[_scrape(r["href"], client) for r in results[:3] if r.get("href")])
    lines = [
        f'[Web search context — live results for: "{query}"]',
        "IMPORTANT: This is real-time data fetched right now. Use it to answer directly.",
        "---",
    ]
    for i, result in enumerate(results):
        page = scraped[i] if i < len(scraped) else ""
        snippet = result.get("body", "")
        content = page if len(page) > len(snippet) else snippet
        lines.append(f"\n## {i+1}. {result.get('title', '')}")
        lines.append(f"Source: {result.get('href', '')}")
        if content:
            lines.append(content)
    lines += ["---", "[End of web search context]"]
    return "\n".join(lines)

# ── Doc context ───────────────────────────────────────────────────────────────
def build_doc_context(project_id: str) -> str:
    knowledge_dir = PROJECTS_ROOT / project_id / "AI-Knowledge"
    if not knowledge_dir.exists():
        return ""
    parts = []
    for md_file in sorted(knowledge_dir.rglob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
            rel = md_file.relative_to(knowledge_dir)
            parts.append(f"### {rel}\n\n{content.strip()}")
        except Exception:
            pass
    if not parts:
        return ""
    header = (
        f"# Project Knowledge: {project_id}\n\n"
        f"The following documents describe the {project_id} project's conventions, "
        f"patterns, and architecture. Use them as authoritative reference.\n\n"
    )
    return header + "\n\n---\n\n".join(parts)


def list_projects() -> list[str]:
    if not PROJECTS_ROOT.exists():
        return []
    return sorted(
        p.name for p in PROJECTS_ROOT.iterdir()
        if p.is_dir() and (p / "AI-Knowledge").exists()
    )

# ── Inject context into message list ─────────────────────────────────────────
def inject_context(messages: list[dict], context: str) -> list[dict]:
    if not context:
        return messages
    if messages and messages[0].get("role") == "system":
        merged = messages[0]["content"] + "\n\n" + context
        return [{"role": "system", "content": merged}] + messages[1:]
    return [{"role": "system", "content": context}] + messages

# ── Input helper ──────────────────────────────────────────────────────────────
def get_input(prompt_text: str, session=None) -> str:
    """Read multiline input. Enter sends, Shift+Enter adds a newline."""
    if HAS_PROMPT_TOOLKIT and session:
        try:
            return session.prompt(prompt_text)
        except (KeyboardInterrupt, EOFError):
            return "/exit"
    try:
        return input(prompt_text)
    except (KeyboardInterrupt, EOFError):
        return "/exit"

# ── Render assistant reply with rich markdown ─────────────────────────────────
def render_reply(text: str):
    console.print()
    console.print(Markdown(text))
    console.print()

# ── Status bar ────────────────────────────────────────────────────────────────
def print_status(model_name: str, web: bool, project: str | None):
    parts = [f"[accent]model:[/accent] {model_name}"]
    parts.append(f"[accent]web:[/accent] {'[green]on[/green]' if web else '[dim]off[/dim]'}")
    if project:
        parts.append(f"[accent]project:[/accent] [green]{project}[/green]")
    else:
        parts.append("[accent]project:[/accent] [dim]none[/dim]")
    console.rule(" · ".join(parts))

# ── Main chat loop ────────────────────────────────────────────────────────────
async def chat_loop(initial_model: str, initial_project: str | None):
    model = initial_model
    web_search = False
    project = initial_project
    history: list[dict] = []   # conversation messages (user + assistant only)

    system_prompt = (
        "You are a helpful, knowledgeable assistant. Be concise and accurate. "
        "When live web search results appear in your context marked [Web search context], "
        "use them to answer directly — do NOT say you lack internet access."
    )

    # Set up prompt_toolkit session
    session = PromptSession(history=InMemoryHistory()) if HAS_PROMPT_TOOLKIT else None

    console.print(Panel(
        "[bold]AI Assistant CLI[/bold]\n"
        "Commands: [cyan]/web[/cyan]  [cyan]/project <name>[/cyan]  "
        "[cyan]/model[/cyan]  [cyan]/clear[/cyan]  [cyan]/help[/cyan]  [cyan]/exit[/cyan]\n"
        "Send message: [dim]Enter[/dim]  │  New line in prompt_toolkit: [dim]Escape + Enter[/dim]",
        border_style="magenta",
    ))

    print_status(model, web_search, project)
    console.print()

    while True:
        # ── Prompt ──
        user_input = get_input("\n[You] › ", session).strip()

        if not user_input:
            continue

        # ── Commands ──
        if user_input.startswith("/"):
            cmd_parts = user_input[1:].split(maxsplit=1)
            cmd = cmd_parts[0].lower()
            arg = cmd_parts[1] if len(cmd_parts) > 1 else ""

            if cmd in ("exit", "quit", "q"):
                console.print("[info]Bye.[/info]")
                break

            elif cmd == "web":
                web_search = not web_search
                console.print(f"[info]Web search {'enabled' if web_search else 'disabled'}.[/info]")
                print_status(model, web_search, project)

            elif cmd == "project":
                if arg.lower() in ("none", "off", ""):
                    project = None
                    console.print("[info]Project context cleared.[/info]")
                else:
                    available = list_projects()
                    if arg in available:
                        project = arg
                        doc_count = len(list((PROJECTS_ROOT / arg / "AI-Knowledge").rglob("*.md")))
                        console.print(f"[info]Loaded project [bold]{arg}[/bold] ({doc_count} docs).[/info]")
                    else:
                        console.print(f"[error]Project '{arg}' not found.[/error]")
                        if available:
                            console.print(f"[info]Available: {', '.join(available)}[/info]")
                print_status(model, web_search, project)

            elif cmd == "model":
                model = CODE_MODEL if model == CHAT_MODEL else CHAT_MODEL
                console.print(f"[info]Switched to [bold]{model}[/bold].[/info]")
                print_status(model, web_search, project)

            elif cmd == "clear":
                history.clear()
                console.print("[info]Conversation cleared.[/info]")

            elif cmd == "help":
                console.print(Panel(
                    "/web              — toggle web search\n"
                    "/project <name>   — load project AI-Knowledge docs\n"
                    "/project none     — clear project context\n"
                    "/model            — switch chat ↔ code model\n"
                    "/clear            — clear conversation history\n"
                    "/exit             — quit",
                    title="Commands", border_style="dim"
                ))

            else:
                console.print(f"[error]Unknown command: /{cmd}[/error]")
            continue

        # ── Build messages for this turn ──
        history.append({"role": "user", "content": user_input})

        messages: list[dict] = [{"role": "system", "content": system_prompt}] + history[:]

        # Inject doc context (stable, loaded once)
        if project:
            doc_ctx = await asyncio.to_thread(build_doc_context, project)
            if doc_ctx:
                messages = inject_context(messages, doc_ctx)

        # Inject web search context (fetched per message)
        if web_search:
            console.print("[info]Searching the web…[/info]")
            web_ctx = await build_web_context(user_input)
            if web_ctx:
                messages = inject_context(messages, web_ctx)

        # ── Stream response ──
        console.print(f"[assistant]\n[{model}][/assistant]")
        reply_parts: list[str] = []

        try:
            async for delta in stream_ollama(messages, model):
                print(delta, end="", flush=True)
                reply_parts.append(delta)
        except RuntimeError as e:
            console.print(f"\n[error]{e}[/error]")
            history.pop()  # remove the user message we just added
            continue

        reply = "".join(reply_parts)
        print()  # newline after streaming

        # Re-render as markdown if the reply likely contains markdown
        if any(c in reply for c in ("```", "##", "**", "- ", "* ")):
            console.print()
            console.print(Markdown(reply))

        history.append({"role": "assistant", "content": reply})

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AI Assistant CLI")
    parser.add_argument("--model", choices=["chat", "code"], default="chat",
                        help="Starting model: chat (qwen3) or code (qwen3-coder)")
    parser.add_argument("--project", default=None,
                        help="Load a project's AI-Knowledge docs at startup")
    args = parser.parse_args()

    model = CODE_MODEL if args.model == "code" else CHAT_MODEL
    asyncio.run(chat_loop(model, args.project))


if __name__ == "__main__":
    main()
