"""Tests for the DeepSeekClient (mocked transport) and client selection.

The client class name is retained, but it targets OpenRouter's free-model
router; the payload must stay a standard OpenAI-compatible request.
"""

from __future__ import annotations

import json

import httpx
import pytest

from autopader.analysis import compute_all
from autopader.data.normalizer import build_case_table, build_reaction_table
from autopader.evidence.packet import packet_for
from autopader.llm.client import DeepSeekClient, EchoClient, LLMError, build_client


def _client(handler):
    return DeepSeekClient(
        api_key="test-key",
        max_backoff_attempts=2,
        transport=httpx.MockTransport(handler),
    )


def _ok_request(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/api/v1/chat/completions"
    payload = json.loads(request.read())
    assert payload["model"] == "openrouter/free"
    assert "thinking" not in payload
    return httpx.Response(200, json={"choices": [{"message": {"content": "narrative text"}}]})


def test_success_response() -> None:
    client = _client(_ok_request)
    out = client.generate([{"role": "user", "content": "hi"}])
    assert out == "narrative text"
    client.close()


def test_empty_content_raises() -> None:
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    client = _client(handler)
    with pytest.raises(LLMError):
        client.generate([])
    client.close()


def test_http_400_not_retried() -> None:
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(400, json={"error": "bad request"})

    client = _client(handler)
    with pytest.raises(LLMError):
        client.generate([])
    assert calls["n"] == 1
    client.close()


def test_http_500_retried_then_fails() -> None:
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(500, json={"error": "boom"})

    client = _client(handler)
    with pytest.raises(LLMError):
        client.generate([])
    assert calls["n"] == 2  # max_backoff_attempts
    client.close()


def test_http_500_then_success() -> None:
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, json={})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = _client(handler)
    assert client.generate([]) == "ok"
    client.close()


def test_timeout_raises_llm_error() -> None:
    def handler(request):
        raise httpx.ReadTimeout("boom")

    client = _client(handler)
    with pytest.raises(LLMError):
        client.generate([])
    client.close()


def test_bad_response_shape_raises() -> None:
    def handler(request):
        return httpx.Response(200, json={"choices": []})

    client = _client(handler)
    with pytest.raises(LLMError):
        client.generate([])
    client.close()


def test_empty_api_key_raises() -> None:
    with pytest.raises(LLMError):
        DeepSeekClient(api_key="", model="x")


def test_build_client_skip_llm_echo(results_fixture) -> None:
    packet = packet_for("narrative_summary", results_fixture)
    client = build_client(packet, skip_llm=True)
    assert isinstance(client, EchoClient)


@pytest.fixture(scope="module")
def results_fixture(real_df_module):
    case_table = build_case_table(real_df_module)
    reaction_df, _ = build_reaction_table(real_df_module)
    return compute_all(case_table, reaction_df, "h")
