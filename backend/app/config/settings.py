"""
Central configuration for RiskLens AI backend.
All values are read from environment variables (.env). Nothing here is
hard-coded secret data — see .env.example for the full list of variables.
"""
import os
from functools import lru_cache


class Settings:
    # --- LLM (Groq only) ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    # If true (or if GROQ_API_KEY is empty), the system runs in MOCK MODE:
    # deterministic, clearly-labelled stand-in text is used instead of a live
    # Groq call so the whole pipeline is still demoable without a key.
    FORCE_MOCK_LLM: bool = os.getenv("FORCE_MOCK_LLM", "false").lower() == "true"

    @property
    def LLM_MOCK_MODE(self) -> bool:
        return self.FORCE_MOCK_LLM or not self.GROQ_API_KEY

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://risklens:risklens@postgres:5432/risklens",
    )

    # --- LangSmith (fully optional) ---
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")

    # --- Investigation graph ---
    MAX_INVESTIGATION_LOOPS: int = int(os.getenv("MAX_INVESTIGATION_LOOPS", "2"))

    # --- Evaluation cost assumptions (synthetic, configurable, clearly labelled) ---
    FALSE_POSITIVE_COST: float = float(os.getenv("FALSE_POSITIVE_COST", "150"))
    FALSE_NEGATIVE_COST: float = float(os.getenv("FALSE_NEGATIVE_COST", "5000"))

    # --- App ---
    APP_ENV: str = os.getenv("APP_ENV", "development")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")


@lru_cache
def get_settings() -> Settings:
    return Settings()
