from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REM_", env_file=".env", extra="ignore")

    app_name: str = "Reverse Engineer Mode API"
    app_version: str = "0.1.0"
    database_url: str = (
        "postgresql+asyncpg://reverse_engineer_mode:local-development-only@"
        "localhost:55432/reverse_engineer_mode"
    )
    redis_url: str = "redis://localhost:56379/0"
    script_provider: Literal["deterministic", "openai_compatible"] = "deterministic"
    provider_base_url: str = "https://api.openai.com/v1"
    provider_model: str = "gpt-5-mini"
    provider_api_key: SecretStr | None = None
    outbox_max_delivery_attempts: int = Field(default=10, ge=1, le=1_000)
    outbox_max_delivery_age_seconds: int = Field(default=3_600, ge=60, le=604_800)
    outbox_retry_base_seconds: int = Field(default=5, ge=1, le=3_600)
    outbox_retry_max_seconds: int = Field(default=300, ge=1, le=86_400)


def provider_api_key_is_configured(value: SecretStr | None) -> bool:
    return value is not None and bool(value.get_secret_value().strip())


settings = Settings()
