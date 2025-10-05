from __future__ import annotations

from typing import List, Optional

from loguru import logger
from mistralai import Mistral
from infra.settings import Settings


class MistralUserAgent:
    """
    Simple wrapper around Mistral chat completions.
    """

    def __init__(self, settings: Optional[Settings] = None, model: str = "mistral-large-latest"):
        self.settings = settings or Settings()
        if not self.settings.MISTRAL_API_KEY:
            logger.warning("MISTRAL_API_KEY missing; Mistral agent disabled.")
        self.client = Mistral(api_key=self.settings.MISTRAL_API_KEY) if self.settings.MISTRAL_API_KEY else None
        self.model = model

    def complete(self, messages: List[dict]) -> Optional[str]:
        if not self.client:
            return None
        try:
            resp = self.client.chat.complete(
                model=self.model,
                messages=messages,
            )
            return resp.choices[0].message.content if resp and resp.choices else None
        except Exception as e:
            logger.error(f"Mistral error: {e}")
            return None
