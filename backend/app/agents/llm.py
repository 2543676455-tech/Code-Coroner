from typing import Protocol

import httpx

from app.core.config import Settings


class LLMClient(Protocol):
    def explain(self, prompt: str) -> str: ...


class OpenAICompatibleClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.llm_enabled:
            raise ValueError("LLM semantic verification is not configured")
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model

    def explain(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Explain only the supplied repository evidence. "
                            "Never invent files, behavior, or test results."
                        ),
                    },
                    {"role": "user", "content": prompt[:12000]},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"])[:2000]


class FakeLLM:
    def __init__(self, response: str = "Evidence is consistent with the rule result.") -> None:
        self.response = response

    def explain(self, prompt: str) -> str:
        del prompt
        return self.response
