"""
AI Assistant — Desktop GUI
Built with CustomTkinter. Talks directly to Ollama (no FastAPI needed).
Supports web search RAG and project knowledge doc injection.
"""

import asyncio
import json
import os
import queue
import threading
import time
from pathlib import Path

import customtkinter as ctk
import httpx

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_URL    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL    = os.getenv("CHAT_MODEL",  "qwen3")
CODE_MODEL    = os.getenv("CODE_MODEL",  "qwen3-coder")
PROJECTS_ROOT = Path(os.getenv("PROJECTS_ROOT", r"C:\Users\quo\repos"))

APP_NAME    = "AI Assistant"
APP_VERSION = "1.0.0"
WIN_W, WIN_H = 1100, 720
SIDEBAR_W    = 220

# Colours (dark theme)
C_BG        = "#0f1117"
C_SIDEBAR   = "#1a1d27"
C_PANEL     = "#1e2433"
C_BORDER    = "#2d3148"
C_ACCENT    = "#6366f1"
C_ACCENT2   = "#4f52cc"
C_TEXT      = "#d1d5db"
C_MUTED     = "#6b7280"
C_USER_BG   = "#1e2433"
C_CODE_BG   = "#161b2e"
C_GREEN     = "#22c55e"
C_RED       = "#ef4444"
C_WHITE     = "#f9fafb"

FONT_BODY   = ("Segoe UI", 13)
FONT_BOLD   = ("Segoe UI", 13, "bold")
FONT_SMALL  = ("Segoe UI", 11)
FONT_MONO   = ("Consolas", 12)
FONT_TITLE  = ("Segoe UI", 15, "bold")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Ollama helpers ─────────────────────────────────────────────────────────────
def stream_ollama_sync(messages: list[dict], model: str, out_queue: queue.Queue):
    """
    Synchronous wrapper — runs in a thread.
    Puts ("delta", text) or ("done", None) or ("error", msg) into out_queue.
    """
    url = f"{OLLAMA_URL}/api/chat"
    payload = {"model": model, "messages": messages, "stream": True}
    timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=5.0)
    try:
        with httpx.Client(timeout=timeout) as client:
            with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    out_queue.put(("error", f"Ollama returned HTTP {resp.status_code}"))
                    return
                for line in resp.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if delta := chunk.get("message", {}).get("content", ""):
                        out_queue.put(("delta", delta))
                    if chunk.get("done"):
                        break
    except httpx.ConnectError:
        out_queue.put(("error", "Could not connect to Ollama — is it running?"))
    except Exception as e:
        out_queue.put(("error", str(e)))
    finally:
        out_queue.put(("done", None))

# ── Web search ─────────────────────────────────────────────────────────────────
def ddg_search(query: str, max_results: int = 5) -> list[dict]:
    delays = [1.5, 3.0, 6.0]
    for attempt, delay in enumerate(delays):
        try:
            from duckduckgo_search import DDGS  # type: ignore
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as exc:
            if attempt == len(delays) - 1:
                return []
            time.sleep(delay)
    return []


def scrape_page(url: str, max_chars: int = 1500) -> str:
    try:
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        with httpx.Client(timeout=httpx.Timeout(connect=5.0, read=8.0)) as client:
            resp = client.get(url, headers=headers, follow_redirects=True)
            if resp.status_code != 200:
                return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        return " ".join(soup.get_text(separator=" ").split())[:max_chars]
    except Exception:
        return ""


def build_web_context(query: str) -> str:
    results = ddg_search(query)
    if not results:
        return ""
    scraped = [scrape_page(r["href"]) for r in results[:3] if r.get("href")]
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

# ── Doc context ────────────────────────────────────────────────────────────────
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
        f"The following documents describe the {project_id} project's conventions and architecture.\n\n"
    )
    return header + "\n\n---\n\n".join(parts)


def list_projects() -> list[str]:
    if not PROJECTS_ROOT.exists():
        return []
    return sorted(
        p.name for p in PROJECTS_ROOT.iterdir()
        if p.is_dir() and (p / "AI-Knowledge").exists()
    )


def inject_context(messages: list[dict], context: str) -> list[dict]:
    if not context:
        return messages
    if messages and messages[0].get("role") == "system":
        merged = messages[0]["content"] + "\n\n" + context
        return [{"role": "system", "content": merged}] + messages[1:]
    return [{"role": "system", "content": context}] + messages

# ── Message bubble widget ──────────────────────────────────────────────────────
class MessageBubble(ctk.CTkFrame):
    def __init__(self, parent, role: str, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.role = role
        self._full_text = ""

        # Role label
        role_label = ctk.CTkLabel(
            self,
            text="You" if role == "user" else "Assistant",
            font=("Segoe UI", 11, "bold"),
            text_color=C_ACCENT if role == "user" else C_GREEN,
            anchor="w",
        )
        role_label.pack(fill="x", padx=4, pady=(6, 2))

        # Content text box
        bg = C_USER_BG if role == "user" else "transparent"
        self.textbox = ctk.CTkTextbox(
            self,
            font=FONT_BODY,
            text_color=C_TEXT,
            fg_color=bg,
            border_width=1 if role == "user" else 0,
            border_color=C_BORDER,
            corner_radius=8,
            wrap="word",
            activate_scrollbars=False,
            height=40,
        )
        self.textbox.pack(fill="x", padx=4, pady=(0, 6))
        self.textbox.configure(state="disabled")

        # Configure tags for basic formatting
        self.textbox.tag_config("code_inline", font=FONT_MONO,
                                foreground="#a78bfa",
                                background=C_CODE_BG)
        self.textbox.tag_config("code_block", font=FONT_MONO,
                                foreground="#d1d5db",
                                background=C_CODE_BG,
                                lmargin1=8, lmargin2=8, rmargin=8)
        self.textbox.tag_config("bold", font=FONT_BOLD)
        self.textbox.tag_config("muted", foreground=C_MUTED)

    def append(self, text: str):
        """Append streaming delta text."""
        self._full_text += text
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text)
        self.textbox.configure(state="disabled")
        self._auto_resize()

    def set_text(self, text: str):
        """Set full text (non-streaming)."""
        self._full_text = text
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
        self.textbox.configure(state="disabled")
        self._auto_resize()

    def _auto_resize(self):
        """Grow the textbox height to fit content without a scrollbar."""
        lines = int(self.textbox.index("end-1c").split(".")[0])
        # Estimate line wraps from content width
        self.textbox.configure(height=max(40, lines * 22 + 12))

# ── Main application window ────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.minsize(700, 500)
        self.configure(fg_color=C_BG)

        # State
        self.history: list[dict] = []
        self.model   = CHAT_MODEL
        self.web_on  = False
        self.project: str | None = None
        self.streaming = False
        self._stream_queue: queue.Queue = queue.Queue()
        self._current_bubble: MessageBubble | None = None

        self.system_prompt = (
            "You are a helpful, knowledgeable assistant. Be concise and accurate. "
            "When live web search results appear in your context marked [Web search context], "
            "use them to answer directly — do NOT say you lack internet access."
        )

        self._build_ui()
        self._refresh_project_list()
        self.after(100, self._poll_stream_queue)

    # ── UI construction ────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Sidebar ──
        self.sidebar = ctk.CTkFrame(self, width=SIDEBAR_W, fg_color=C_SIDEBAR,
                                    corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Title
        ctk.CTkLabel(self.sidebar, text="AI Assistant",
                     font=FONT_TITLE, text_color=C_WHITE).pack(pady=(20, 4), padx=16, anchor="w")
        ctk.CTkLabel(self.sidebar, text=f"v{APP_VERSION}",
                     font=FONT_SMALL, text_color=C_MUTED).pack(padx=16, anchor="w")

        self._sidebar_divider()

        # Model selector
        ctk.CTkLabel(self.sidebar, text="MODEL", font=("Segoe UI", 10, "bold"),
                     text_color=C_MUTED).pack(padx=16, pady=(12, 4), anchor="w")
        self.model_var = ctk.StringVar(value="Chat (qwen3)")
        self.model_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Chat (qwen3)", "Code (qwen3-coder)"],
            variable=self.model_var,
            command=self._on_model_change,
            fg_color=C_PANEL,
            button_color=C_ACCENT,
            button_hover_color=C_ACCENT2,
            text_color=C_TEXT,
            width=SIDEBAR_W - 32,
        )
        self.model_menu.pack(padx=16)

        self._sidebar_divider()

        # Web search toggle
        ctk.CTkLabel(self.sidebar, text="WEB SEARCH", font=("Segoe UI", 10, "bold"),
                     text_color=C_MUTED).pack(padx=16, pady=(12, 4), anchor="w")
        self.web_var = ctk.BooleanVar(value=False)
        self.web_switch = ctk.CTkSwitch(
            self.sidebar,
            text="Search before reply",
            variable=self.web_var,
            command=self._on_web_toggle,
            font=FONT_SMALL,
            text_color=C_TEXT,
            progress_color=C_GREEN,
            button_color=C_WHITE,
        )
        self.web_switch.pack(padx=16, anchor="w")
        self.web_label = ctk.CTkLabel(self.sidebar, text="Off",
                                      font=FONT_SMALL, text_color=C_MUTED)
        self.web_label.pack(padx=16, anchor="w")

        self._sidebar_divider()

        # Project selector
        ctk.CTkLabel(self.sidebar, text="PROJECT KNOWLEDGE", font=("Segoe UI", 10, "bold"),
                     text_color=C_MUTED).pack(padx=16, pady=(12, 4), anchor="w")
        self.project_var = ctk.StringVar(value="None")
        self.project_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["None"],
            variable=self.project_var,
            command=self._on_project_change,
            fg_color=C_PANEL,
            button_color=C_ACCENT,
            button_hover_color=C_ACCENT2,
            text_color=C_TEXT,
            width=SIDEBAR_W - 32,
        )
        self.project_menu.pack(padx=16)
        self.project_label = ctk.CTkLabel(self.sidebar, text="No docs loaded",
                                          font=FONT_SMALL, text_color=C_MUTED,
                                          wraplength=SIDEBAR_W - 32)
        self.project_label.pack(padx=16, anchor="w", pady=(4, 0))

        self._sidebar_divider()

        # Clear button
        ctk.CTkButton(
            self.sidebar, text="New Conversation", command=self._clear_chat,
            fg_color=C_PANEL, hover_color=C_BORDER, text_color=C_TEXT,
            width=SIDEBAR_W - 32, font=FONT_SMALL,
        ).pack(padx=16, pady=(12, 0))

        # ── Main panel ──
        main = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        main.pack(side="left", fill="both", expand=True)

        # Status bar at top
        self.status_bar = ctk.CTkLabel(
            main, text="", font=FONT_SMALL, text_color=C_MUTED,
            fg_color=C_SIDEBAR, anchor="w", height=28,
        )
        self.status_bar.pack(fill="x")
        self._update_status()

        # Scrollable message area
        self.msg_frame = ctk.CTkScrollableFrame(
            main, fg_color=C_BG, scrollbar_button_color=C_BORDER,
            scrollbar_button_hover_color=C_ACCENT,
        )
        self.msg_frame.pack(fill="both", expand=True, padx=0, pady=0)
        self.msg_frame.columnconfigure(0, weight=1)

        self._add_welcome()

        # Input area
        input_frame = ctk.CTkFrame(main, fg_color=C_SIDEBAR,
                                   corner_radius=0, height=100)
        input_frame.pack(fill="x", side="bottom")
        input_frame.pack_propagate(False)

        self.input_box = ctk.CTkTextbox(
            input_frame,
            height=60,
            font=FONT_BODY,
            fg_color=C_PANEL,
            text_color=C_TEXT,
            border_color=C_BORDER,
            border_width=1,
            corner_radius=8,
            wrap="word",
        )
        self.input_box.pack(side="left", fill="both", expand=True, padx=(12, 8), pady=12)
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)  # allow newline

        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.pack(side="right", padx=(0, 12), pady=12, fill="y")

        self.send_btn = ctk.CTkButton(
            btn_frame, text="Send", command=self._send,
            fg_color=C_ACCENT, hover_color=C_ACCENT2,
            font=FONT_BOLD, width=80, height=60,
            corner_radius=8,
        )
        self.send_btn.pack()

    def _sidebar_divider(self):
        ctk.CTkFrame(self.sidebar, height=1, fg_color=C_BORDER).pack(
            fill="x", padx=16, pady=8)

    def _add_welcome(self):
        frame = ctk.CTkFrame(self.msg_frame, fg_color="transparent")
        frame.pack(fill="x", padx=32, pady=60)
        ctk.CTkLabel(
            frame, text="AI Assistant",
            font=("Segoe UI", 28, "bold"), text_color=C_WHITE,
        ).pack()
        ctk.CTkLabel(
            frame,
            text="Powered by local Ollama models — no cloud, no latency.\n"
                 "Toggle web search or load a project's knowledge docs from the sidebar.",
            font=FONT_BODY, text_color=C_MUTED, justify="center",
        ).pack(pady=(8, 0))

    # ── Sidebar callbacks ─────────────────────────────────────────────────────
    def _on_model_change(self, value: str):
        self.model = CODE_MODEL if "code" in value.lower() else CHAT_MODEL
        self._update_status()

    def _on_web_toggle(self):
        self.web_on = self.web_var.get()
        self.web_label.configure(
            text="On — will search before each reply" if self.web_on else "Off",
            text_color=C_GREEN if self.web_on else C_MUTED,
        )
        self._update_status()

    def _on_project_change(self, value: str):
        self.project = None if value == "None" else value
        if self.project:
            doc_count = len(list((PROJECTS_ROOT / self.project / "AI-Knowledge").rglob("*.md")))
            self.project_label.configure(
                text=f"{doc_count} docs loaded",
                text_color=C_GREEN,
            )
        else:
            self.project_label.configure(text="No docs loaded", text_color=C_MUTED)
        self._update_status()

    def _refresh_project_list(self):
        projects = list_projects()
        values = ["None"] + projects
        self.project_menu.configure(values=values)

    def _clear_chat(self):
        self.history.clear()
        for w in self.msg_frame.winfo_children():
            w.destroy()
        self._add_welcome()
        self._update_status("Conversation cleared")

    def _update_status(self, extra: str = ""):
        web = "🌐 Web ON" if self.web_on else ""
        proj = f"📚 {self.project}" if self.project else ""
        parts = [p for p in [self.model, web, proj, extra] if p]
        self.status_bar.configure(text="  " + "  ·  ".join(parts))

    # ── Send message ──────────────────────────────────────────────────────────
    def _on_enter(self, event):
        # Enter sends; Shift+Enter inserts newline
        if not event.state & 0x1:   # Shift not held
            self._send()
            return "break"

    def _send(self):
        if self.streaming:
            return
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            return
        self.input_box.delete("1.0", "end")
        self._add_message("user", text)
        self.history.append({"role": "user", "content": text})
        self.send_btn.configure(state="disabled", text="…")
        self.streaming = True
        threading.Thread(target=self._run_stream, args=(text,), daemon=True).start()

    def _run_stream(self, user_text: str):
        """Runs in background thread — no tk calls allowed here."""
        messages = [{"role": "system", "content": self.system_prompt}] + self.history[:-1]
        messages.append({"role": "user", "content": user_text})

        # Inject doc context
        if self.project:
            doc_ctx = build_doc_context(self.project)
            if doc_ctx:
                messages = inject_context(messages, doc_ctx)

        # Inject web context
        if self.web_on:
            self._stream_queue.put(("status", "Searching the web…"))
            web_ctx = build_web_context(user_text)
            if web_ctx:
                messages = inject_context(messages, web_ctx)

        self._stream_queue.put(("status", ""))
        self._stream_queue.put(("start_assistant", None))
        stream_ollama_sync(messages, self.model, self._stream_queue)

    def _add_message(self, role: str, text: str = "") -> MessageBubble:
        # Remove welcome message on first real message
        children = self.msg_frame.winfo_children()
        if children and isinstance(children[0], ctk.CTkFrame) and len(children) == 1:
            try:
                label = children[0].winfo_children()[0]
                if isinstance(label, ctk.CTkLabel) and "AI Assistant" in str(label.cget("text")):
                    children[0].destroy()
            except Exception:
                pass

        bubble = MessageBubble(self.msg_frame, role)
        bubble.pack(fill="x", padx=24, pady=2)
        if text:
            bubble.set_text(text)
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self):
        self.msg_frame._parent_canvas.yview_moveto(1.0)

    # ── Stream queue polling ──────────────────────────────────────────────────
    def _poll_stream_queue(self):
        try:
            while True:
                event, data = self._stream_queue.get_nowait()

                if event == "status":
                    self._update_status(data)

                elif event == "start_assistant":
                    self._current_bubble = self._add_message("assistant")

                elif event == "delta":
                    if self._current_bubble:
                        self._current_bubble.append(data)
                        self._scroll_to_bottom()

                elif event == "error":
                    if self._current_bubble:
                        self._current_bubble.set_text(f"⚠ {data}")
                        self._current_bubble.textbox.configure(text_color=C_RED)
                    self._finish_stream()

                elif event == "done":
                    if self._current_bubble:
                        reply = self._current_bubble._full_text
                        self.history.append({"role": "assistant", "content": reply})
                    self._finish_stream()

        except queue.Empty:
            pass
        self.after(50, self._poll_stream_queue)

    def _finish_stream(self):
        self.streaming = False
        self._current_bubble = None
        self.send_btn.configure(state="normal", text="Send")
        self._update_status()
        self._scroll_to_bottom()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
