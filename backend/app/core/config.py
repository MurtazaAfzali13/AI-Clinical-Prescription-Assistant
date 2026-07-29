"""
Application configuration.

All runtime configuration is centralised here and loaded from environment
variables (via a local `.env` file in development). Never hardcode secrets.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- General ---
    app_name: str = "Doctor Copilot System"
    api_v1_prefix: str = "/api/v1"
    environment: str = Field(default="development")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    openrouter_api_key: str = Field(default="")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    llm_model_name: str = Field(default="openai/gpt-4o-mini")
    llm_temperature: float = Field(default=0.0)
    embedding_model: str = Field(default="openai/text-embedding-3-small")

    # --- Pinecone (RAG / drug interaction vector store) ---
    pinecone_api_key: str = Field(default="")
    index_name: str = Field(default="drug-knowledge-base")

    # --- Supabase (Postgres) ---
    supabase_url: str = Field(default="")
    supabase_service_key: str = Field(default="")
    supabase_jwt_secret: str = Field(default="", description="Used to verify doctor auth tokens")

    def validate_for_ingestion(self) -> None:
        """Raise a clear error before an ingestion run if required keys are missing."""
        missing = [
            name
            for name, value in (
                ("OPENROUTER_API_KEY", self.openrouter_api_key),
                ("PINECONE_API_KEY", self.pinecone_api_key),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required settings for ingestion: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (singleton for the process lifetime)."""
    return Settings()