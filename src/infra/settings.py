from __future__ import annotations

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class Settings(BaseSettings):
    # API keys
    MISTRAL_API_KEY: str = Field(default="", description="Mistral API key")
    GOOGLE_GENAI_API_KEY: str = Field(default="", description="Google Generative AI key")

    # App configuration
    APP_MODE: str = Field(default="dev")
    RANDOM_SEED: int = Field(default=42)
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def __init__(self, **values):
        super().__init__(**values)
        # optional: propagate log level
        os.environ.setdefault("LOGURU_LEVEL", self.LOG_LEVEL)
