import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services.llm_provider import (
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderUnavailableError,
    OllamaLLMProvider,
    get_llm_provider,
)


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self, chunk_size: int):
        yield self.content


def _ollama_settings(**overrides) -> Settings:
    values = {
        "llm_provider": "ollama",
        "llm_api_url": "http://127.0.0.1:11434",
        "llm_model_name": "synthetic-local-model",
        "llm_model_version": "synthetic-v1",
    }
    values.update(overrides)
    return Settings(**values)


def test_ollama_adapter_uses_existing_provider_interface_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def fake_stream(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["payload"] = kwargs["json"]
        captured["timeout"] = kwargs["timeout"]
        captured["headers"] = kwargs["headers"]
        return FakeResponse(b'{"message":{"content":"{}"}}')

    monkeypatch.setattr("app.core.provider_http.httpx.stream", fake_stream)
    provider = get_llm_provider(_ollama_settings())

    assert isinstance(provider, OllamaLLMProvider)
    assert provider.answer_legal_question(
        "Synthetic question?",
        [{"text": "Synthetic fixture evidence."}],
    ) == "{}"
    assert captured["method"] == "POST"
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["payload"]["model"] == "synthetic-local-model"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["messages"][1]["content"] == json.dumps(
        {
            "question": "Synthetic question?",
            "retrieved_evidence": [{"text": "Synthetic fixture evidence."}],
        },
        ensure_ascii=False,
    )
    assert captured["timeout"] > 0
    assert "Authorization" not in captured["headers"]


def test_ollama_rate_limit_is_reported_distinctly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_stream(method, url, **kwargs):
        response = httpx.Response(
            429,
            request=httpx.Request(method, url),
        )
        class RateLimitedResponse(FakeResponse):
            def raise_for_status(self) -> None:
                response.raise_for_status()

        return RateLimitedResponse(b"{}")

    monkeypatch.setattr("app.core.provider_http.httpx.stream", fake_stream)
    provider = OllamaLLMProvider(_ollama_settings())

    with pytest.raises(LLMProviderRateLimitError, match="rate limit"):
        provider.answer_legal_question("Synthetic question?", [])


def test_ollama_connection_failure_is_reported_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_stream(*args, **kwargs):
        raise httpx.ConnectError("synthetic connection failure")

    monkeypatch.setattr("app.core.provider_http.httpx.stream", fake_stream)
    provider = OllamaLLMProvider(_ollama_settings())

    with pytest.raises(LLMProviderUnavailableError, match="unavailable"):
        provider.answer_legal_question("Synthetic question?", [])


def test_ollama_rejects_missing_model_configuration() -> None:
    with pytest.raises(LLMProviderUnavailableError, match="installed Ollama model"):
        OllamaLLMProvider(_ollama_settings(llm_model_name="not-configured"))


def test_ollama_missing_installed_model_is_reported_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_stream(method, url, **kwargs):
        response = httpx.Response(
            404,
            request=httpx.Request(method, url),
        )

        class MissingModelResponse(FakeResponse):
            def raise_for_status(self) -> None:
                response.raise_for_status()

        return MissingModelResponse(b"{}")

    monkeypatch.setattr("app.core.provider_http.httpx.stream", fake_stream)
    provider = OllamaLLMProvider(_ollama_settings())

    with pytest.raises(LLMProviderUnavailableError, match="configured model"):
        provider.answer_legal_question("Synthetic question?", [])


def test_ollama_rejects_remote_plain_http_url() -> None:
    with pytest.raises(LLMProviderError, match="invalid or insecure"):
        OllamaLLMProvider(
            _ollama_settings(llm_api_url="http://ollama.example:11434")
        )


def test_ollama_rejects_ignored_api_key() -> None:
    with pytest.raises(LLMProviderError, match="does not support API-key"):
        OllamaLLMProvider(
            _ollama_settings(llm_api_key=SecretStr("synthetic-secret"))
        )


def test_ollama_rejects_invalid_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.core.provider_http.httpx.stream",
        lambda *args, **kwargs: FakeResponse(b"not-json"),
    )
    provider = OllamaLLMProvider(_ollama_settings())

    with pytest.raises(LLMProviderError, match="invalid response"):
        provider.answer_legal_question("Synthetic question?", [])
