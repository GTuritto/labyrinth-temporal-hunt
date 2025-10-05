from __future__ import annotations

from typing import List, Optional

import google.generativeai as genai
from loguru import logger
from infra.settings import Settings


class GeminiMinotaurAgent:
    """
    Simple wrapper around Google Generative AI (Gemini) for Minotaur behavior.
    """

    def __init__(self, settings: Optional[Settings] = None, model: str = "gemini-1.5-pro"):
        self.settings = settings or Settings()
        if not self.settings.GOOGLE_GENAI_API_KEY:
            logger.warning("GOOGLE_GENAI_API_KEY missing; Gemini agent disabled.")
            self.client = None
        else:
            genai.configure(api_key=self.settings.GOOGLE_GENAI_API_KEY)
            self.client = genai.GenerativeModel(model_name=model)
        self.model = model

    def complete(self, messages: List[dict]) -> Optional[str]:
        """
        messages: list of {role, content}
        """
        if not self.client:
            return None
        try:
            # Flatten simple conversation content into a single prompt
            prompt = "\n".join([f"{m.get('role','user')}: {m.get('content','')}" for m in messages])
            resp = self.client.generate_content(prompt)
            if hasattr(resp, "text"):
                return resp.text
            # Fallbacks if SDK returns different struct
            candidates = getattr(resp, "candidates", None)
            if candidates and candidates[0].content.parts:
                return candidates[0].content.parts[0].text
            return None
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return None
