import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services import legal_question_answering
from app.services.llm_provider import (
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderUnavailableError,
    GeminiLLMProvider,
    OllamaLLMProvider,
    get_contract_analysis_provider,
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


def _gemini_settings(**overrides) -> Settings:
    values = {
        "llm_provider": "gemini",
        "llm_api_key": SecretStr("synthetic-gemini-key"),
        "llm_model_name": "gemini-2.5-flash-lite",
        "llm_model_version": "synthetic-v1",
    }
    values.update(overrides)
    return Settings(**values)


def test_gemini_adapter_uses_existing_interface_and_keeps_key_out_of_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}
    response_text = json.dumps(
        {
            "answer": "Synthetic answer",
            "evidence_assessment": "supporting",
            "citations": [],
        }
    )

    def fake_post(url, *, payload, headers, timeout, max_response_bytes):
        captured.update(
            url=url,
            payload=payload,
            headers=headers,
            timeout=timeout,
            max_response_bytes=max_response_bytes,
        )
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": response_text[:20]},
                            {"text": response_text[20:]},
                        ]
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.llm_provider.post_bounded_json", fake_post)
    provider = get_llm_provider(_gemini_settings())

    assert isinstance(provider, GeminiLLMProvider)
    assert provider.answer_legal_question(
        "Synthetic question?",
        [{"text": "Synthetic fixture evidence."}],
    ) == response_text
    assert captured["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash-lite:generateContent"
    )
    assert "synthetic-gemini-key" not in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "synthetic-gemini-key"
    assert "synthetic-gemini-key" not in json.dumps(captured["payload"])
    assert captured["payload"]["generationConfig"] == {
        "temperature": 0,
        "responseMimeType": "application/json",
    }
    assert "untrusted data" in captured["payload"]["systemInstruction"]["parts"][0]["text"]
    user_content = captured["payload"]["contents"][0]["parts"][0]["text"]
    assert "Synthetic question?" in user_content
    assert captured["timeout"] > 0
    assert captured["max_response_bytes"] == 1_000_000


def test_gemini_contract_prompt_defines_the_audit_response_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.schemas.compliance_analysis import LLMClauseAnalysis

    captured = {}
    response_text = json.dumps(
        {
            "category": "insufficient_evidence",
            "severity": "informational",
            "explanation": "No legal evidence was supplied.",
            "recommended_action": None,
            "evidence_assessment": "insufficient",
            "citations": [],
            "model_confidence": None,
        }
    )

    def fake_post(url, *, payload, **kwargs):
        captured["system"] = payload["systemInstruction"]["parts"][0]["text"]
        return {
            "candidates": [
                {"content": {"parts": [{"text": response_text}]}}
            ]
        }

    monkeypatch.setattr("app.services.llm_provider.post_bounded_json", fake_post)
    provider = GeminiLLMProvider(_gemini_settings())

    parsed = LLMClauseAnalysis.model_validate(
        json.loads(
            provider.analyze_clause(
                {"clause_id": "synthetic-clause", "original_text": "Synthetic text"},
                [],
            )
        )
    )

    assert parsed.category == "insufficient_evidence"
    assert "recommended_action" in captured["system"]
    assert "supporting_quote" in captured["system"]
    assert "Do not return clause_id" in captured["system"]


def test_gemini_provider_factory_requires_api_key() -> None:
    with pytest.raises(LLMProviderUnavailableError, match="API key"):
        get_llm_provider(_gemini_settings(llm_api_key=None))


def test_legal_qa_provider_override_does_not_enable_audit_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        llm_provider="disabled",
        legal_qa_llm_provider="gemini",
        llm_api_key=SecretStr("synthetic-gemini-key"),
        llm_model_name="gemini-2.5-flash-lite",
    )
    captured = {}

    def fake_get_provider(provider_settings=None):
        captured["settings"] = provider_settings
        return object()

    monkeypatch.setattr(legal_question_answering, "get_settings", lambda: settings)
    monkeypatch.setattr(
        legal_question_answering,
        "get_llm_provider",
        fake_get_provider,
    )

    legal_question_answering._get_legal_question_provider()

    assert settings.llm_provider == "disabled"
    assert captured["settings"].llm_provider == "gemini"
    assert captured["settings"].legal_qa_llm_provider == "gemini"


def test_contract_provider_override_is_explicit_and_backward_compatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        llm_provider="disabled",
        contract_analysis_llm_provider="gemini",
        llm_api_key=SecretStr("synthetic-gemini-key"),
        llm_model_name="gemini-2.5-flash-lite",
    )
    captured = {}

    def fake_get_provider(provider_settings=None):
        captured["settings"] = provider_settings
        return object()

    monkeypatch.setattr("app.services.llm_provider.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.llm_provider.get_llm_provider", fake_get_provider)

    get_contract_analysis_provider()

    assert settings.llm_provider == "disabled"
    assert captured["settings"].llm_provider == "gemini"
    assert captured["settings"].contract_analysis_llm_provider == "gemini"


def test_contract_provider_uses_existing_shared_provider_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(llm_provider="ollama")
    captured = {}

    def fake_get_provider(provider_settings=None):
        captured["settings"] = provider_settings
        return object()

    monkeypatch.setattr("app.services.llm_provider.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.llm_provider.get_llm_provider", fake_get_provider)

    get_contract_analysis_provider()

    assert captured["settings"] is settings


def test_gemini_rate_limit_is_reported_distinctly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def rate_limited(*args, **kwargs):
        request = httpx.Request("POST", args[0])
        response = httpx.Response(429, request=request)
        raise httpx.HTTPStatusError(
            "synthetic provider limit",
            request=request,
            response=response,
        )

    monkeypatch.setattr("app.services.llm_provider.post_bounded_json", rate_limited)
    provider = GeminiLLMProvider(_gemini_settings())

    with pytest.raises(LLMProviderRateLimitError, match="rate limit"):
        provider.answer_legal_question("Synthetic question?", [])


def test_gemini_missing_model_is_reported_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_model(*args, **kwargs):
        request = httpx.Request("POST", args[0])
        response = httpx.Response(404, request=request)
        raise httpx.HTTPStatusError(
            "synthetic missing model",
            request=request,
            response=response,
        )

    monkeypatch.setattr("app.services.llm_provider.post_bounded_json", missing_model)
    provider = GeminiLLMProvider(_gemini_settings())

    with pytest.raises(LLMProviderUnavailableError, match="model is unavailable"):
        provider.answer_legal_question("Synthetic question?", [])


def test_gemini_connection_failure_is_reported_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("synthetic connection failure")

    monkeypatch.setattr("app.services.llm_provider.post_bounded_json", unavailable)
    provider = GeminiLLMProvider(_gemini_settings())

    with pytest.raises(LLMProviderUnavailableError, match="unavailable"):
        provider.answer_legal_question("Synthetic question?", [])


def test_gemini_retries_one_transient_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    response = {
        "candidates": [
            {"content": {"parts": [{"text": '{"answer":"Synthetic"}'}]}}
        ]
    }

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("synthetic connection failure")
        return response

    monkeypatch.setattr("app.services.llm_provider.post_bounded_json", fail_once)
    monkeypatch.setattr("app.services.llm_provider.time.sleep", lambda _: None)
    provider = GeminiLLMProvider(_gemini_settings())

    assert provider.answer_legal_question("Synthetic question?", []) == (
        '{"answer":"Synthetic"}'
    )
    assert calls == 2


def test_gemini_retries_transient_server_error_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def unavailable(*args, **kwargs):
        nonlocal calls
        calls += 1
        request = httpx.Request("POST", args[0])
        response = httpx.Response(503, request=request)
        raise httpx.HTTPStatusError(
            "synthetic service failure",
            request=request,
            response=response,
        )

    monkeypatch.setattr("app.services.llm_provider.post_bounded_json", unavailable)
    monkeypatch.setattr("app.services.llm_provider.time.sleep", lambda _: None)
    provider = GeminiLLMProvider(_gemini_settings())

    with pytest.raises(LLMProviderUnavailableError, match="temporarily unavailable"):
        provider.answer_legal_question("Synthetic question?", [])
    assert calls == 2


def test_gemini_invalid_response_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.llm_provider.post_bounded_json",
        lambda *args, **kwargs: {"candidates": []},
    )
    provider = GeminiLLMProvider(_gemini_settings())

    with pytest.raises(LLMProviderError, match="invalid response"):
        provider.answer_legal_question("Synthetic question?", [])


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
