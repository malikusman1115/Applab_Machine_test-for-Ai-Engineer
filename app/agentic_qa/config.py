from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic QA Service"
    request_timeout_seconds: float = Field(default=8.0, gt=0)
    retry_attempts: int = Field(default=2, ge=0, le=5)
    cache_ttl_seconds: int = Field(default=300, ge=0)
    max_concurrent_tools: int = Field(default=8, ge=1, le=100)
    allowed_domains: list[str] = Field(default_factory=lambda: ["api.duckduckgo.com"])
    model_config = SettingsConfigDict(env_file=".env", env_prefix="AGENTIC_QA_", extra="ignore")


settings = Settings()
