from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    chat_model: str = "qwen3"
    code_model: str = "qwen3-coder"
    cors_origins: str = "http://localhost:5173"
    model_provider: Literal["ollama", "openai", "anthropic", "openrouter"] = "ollama"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openrouter_api_key: str | None = None
    projects_root: str = r"C:\Users\quo\repos"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
