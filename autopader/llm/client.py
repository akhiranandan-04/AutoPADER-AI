"""Thin LLM clients behind a common ``generate(messages) -> str`` interface.

The live endpoint is OpenAI-compatible; we call ``POST {base_url}/chat/completions``
directly with httpx. The client targets OpenRouter's free-model router
(``openrouter/free``) while keeping the ``DeepSeekClient`` class name for
interface stability. ``EchoClient`` produces a deterministic echo for tests and
``--skip-llm`` runs (no network, no API key).
"""

from __future__ import annotations

import time
from typing import Protocol

import httpx

from ..evidence.packet import EvidencePacket

DEFAULT_MODEL = "openrouter/free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
TEMPERATURE = 0.2
MAX_TOKENS = 1500


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    name: str

    def generate(self, messages: list[dict]) -> str: ...


def _timeout() -> httpx.Timeout:
    return httpx.Timeout(connect=10, read=120, write=120, pool=10)


class DeepSeekClient:
    """OpenAI-compatible chat client for OpenRouter free models.

    The class name is retained for interface stability; the client talks to
    OpenRouter's OpenAI-compatible endpoint (``openrouter/free``).
    """

    name = DEFAULT_MODEL

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        max_backoff_attempts: int = 3,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise LLMError("OpenRouter API key is empty; set OPENROUTER_API_KEY or use --skip-llm")
        self._model = model
        self.name = model
        if transport is None:
            transport = httpx.HTTPTransport(retries=2)
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=_timeout(),
            transport=transport,  # type: ignore[arg-type]
        )
        self._max_backoff_attempts = max_backoff_attempts

    def generate(self, messages: list[dict], temperature: float = TEMPERATURE) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": MAX_TOKENS,
            "stream": False,
        }
        last_error: Exception | None = None
        for attempt in range(self._max_backoff_attempts):
            try:
                response = self._http.post("/chat/completions", json=payload)
                if response.status_code == 200:
                    content = self._parse_content(response.json())
                    if not content:
                        raise LLMError("LLM returned empty content")
                    return content
                if 400 <= response.status_code < 500:
                    # never retry client errors
                    raise LLMError(f"LLM HTTP {response.status_code}: {response.text[:300]}")
                # 429 or 5xx: bounded exponential backoff
                last_error = LLMError(f"LLM HTTP {response.status_code}: {response.text[:200]}")
            except httpx.TimeoutException as exc:
                last_error = LLMError(f"LLM request timed out: {exc}")
            except httpx.HTTPError as exc:
                last_error = LLMError(f"LLM transport error: {exc}")
            delay = 2**attempt
            time.sleep(delay)
        raise LLMError(str(last_error or "LLM request failed"))

    @staticmethod
    def _parse_content(data: object) -> str:
        try:
            return str(data["choices"][0]["message"]["content"])  # type: ignore[index]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unexpected LLM response shape: {exc}") from exc

    def close(self) -> None:
        self._http.close()


class EchoClient:
    """Deterministic client that echoes the evidence table without any call.

    The echoed text only ever contains packet values, so the grounding check
    passes by construction — useful for pipeline tests and --skip-llm runs.
    """

    name = "echo"

    def __init__(self, packet: EvidencePacket) -> None:
        self._packet = packet

    def generate(self, messages: list[dict]) -> str:
        from .prompts import render_evidence_table

        return render_evidence_table(self._packet)


def build_client(packet: EvidencePacket, skip_llm: bool = False) -> LLMClient:
    """Choose the real client or the deterministic echo client."""
    if skip_llm:
        return EchoClient(packet)
    from ..config.settings import load_settings

    settings = load_settings()
    if not settings.openrouter_api_key:
        return EchoClient(packet)
    return DeepSeekClient(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        model=settings.openrouter_model,
    )
