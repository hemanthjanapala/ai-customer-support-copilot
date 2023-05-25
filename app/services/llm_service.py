"""LLM provider client.

Phase 2: real OpenAI calls with timeout, one retry on transient failures,
and token accounting for cost observability.

When no API key is configured the service reports not-configured and the
API layer falls back to the Phase 1 mocks (degraded mode, same as a
feature flag). This keeps tests and local dev working without a key.
"""

import time
from dataclasses import dataclass

from app.config import settings


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    status: str  # ok
    model: str


class LLMService:
    def __init__(self) -> None:
        self._api_key = settings.openai_api_key
        self._model = settings.openai_model
        self._timeout_s = settings.llm_timeout_s
        self._client = None

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key, timeout=self._timeout_s)
        return self._client

    def complete(
        self, system: str, user: str, max_tokens: int, temperature: float
    ) -> LLMResult:
        """One chat completion with a single retry on transient failures."""
        if not self.is_configured():
            raise RuntimeError("LLM not configured: set OPENAI_API_KEY")
        from openai import APIStatusError, APITimeoutError

        client = self._get_client()
        last_exc: Exception | None = None
        for attempt in range(2):
            t0 = time.time()
            try:
                resp = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                latency_ms = int((time.time() - t0) * 1000)
                usage = resp.usage
                return LLMResult(
                    text=(resp.choices[0].message.content or "").strip(),
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=latency_ms,
                    status="ok",
                    model=self._model,
                )
            except APITimeoutError as e:
                last_exc = e
            except APIStatusError as e:
                last_exc = e
                if e.status_code is not None and e.status_code < 500:
                    break  # client error: retrying won't help
            time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"LLM call failed after retry: {last_exc}")


llm_service = LLMService()
