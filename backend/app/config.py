"""Application configuration, loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg2://triage:triage@localhost:5432/triage"

    # CORS — comma-separated origins for the SPA
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- AI triage ---
    # When false, every ticket falls back to manual triage without an API call.
    triage_enabled: bool = True
    anthropic_api_key: str | None = None
    # Triage is a cheap, bounded classification — Haiku is the sensible default.
    triage_model: str = "claude-haiku-4-5-20251001"
    triage_max_tokens: int = 512
    # Hard wall on the external call so ticket creation never hangs on the LLM.
    triage_timeout_seconds: float = 12.0
    # Suggestions below this confidence are discarded into the manual fallback.
    triage_confidence_threshold: float = 0.6

    # --- AI reply drafting ---
    # Same responsible-AI pattern as triage; a draft is always agent-editable.
    reply_enabled: bool = True
    reply_model: str = "claude-haiku-4-5-20251001"
    reply_max_tokens: int = 1024
    reply_timeout_seconds: float = 20.0
    reply_confidence_threshold: float = 0.5

    # --- Auth ---
    # When false, the API is open (single-agent demo) and events have no actor.
    auth_enabled: bool = False
    jwt_secret: str = "dev-only-change-me-in-production-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
