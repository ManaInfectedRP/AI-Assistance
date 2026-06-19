from typing import Literal
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = True
    temperature: float = 0.7
    max_tokens: int | None = None
    web_search: bool = False


class ChatChunk(BaseModel):
    delta: str
    done: bool
