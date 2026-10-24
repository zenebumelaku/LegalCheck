import json

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services.embeddings import (
    EMBEDDING_DIMENSIONS,
    EmbeddingProviderConfigurationError,
    EmbeddingProviderError,
    OpenAICompatibleEmbeddingProvider,
)


def test_embedding_credentials_require_https() -> None:
    with pytest.raises(
        EmbeddingProviderConfigurationError,
        match="invalid or insecure",
    ):
        OpenAICompatibleEmbeddingProvider(
            endpoint="http://embedding.example/v1",
            model_name="test-model",
            model_version="test-v1",
            api_key="test-only-secret",
        )


def test_embedding_provider_rejects_plain_http_to_remote_host() -> None:
    with pytest.raises(
        EmbeddingProviderConfigurationError,
        match="invalid or insecure",
    ):
        OpenAICompatibleEmbeddingProvider(
            endpoint="http://embedding.example/v1",
            model_name="test-model",
            model_version="test-v1",
            api_key=None,
        )


def test_embedding_provider_allows_unauthenticated_local_development_endpoint() -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        endpoint="http://127.0.0.1:8080/v1",
        model_name="test-model",
        model_version="test-v1",
        api_key=None,
    )

    assert provider.endpoint == "http://127.0.0.1:8080/v1"


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://user:password@embedding.example/v1",
        "https://embedding.example/v1?api_key=secret",
        "javascript:alert(1)",
        "/relative/path",
    ],
)
def test_embedding_provider_rejects_unsafe_endpoint_values(endpoint: str) -> None:
    with pytest.raises(EmbeddingProviderConfigurationError):
        OpenAICompatibleEmbeddingProvider(
            endpoint=endpoint,
            model_name="test-model",
            model_version="test-v1",
            api_key=None,
        )


def test_embedding_provider_reads_only_bounded_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, int] = {}

    class OversizedResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            captured["read_limit"] = size
            return b" " * size

    def fake_urlopen(request, timeout):
        return OversizedResponse()

    monkeypatch.setattr("app.services.embeddings.urlopen", fake_urlopen)
    provider = OpenAICompatibleEmbeddingProvider(
        endpoint="https://embedding.example/v1",
        model_name="test-model",
        model_version="test-v1",
        api_key=None,
    )

    with pytest.raises(
        EmbeddingProviderError,
        match="request failed",
    ):
        provider.embed(["synthetic test input"])

    assert captured["read_limit"] == 1_000_001


def test_embedding_provider_sends_key_only_to_https(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            vector = [0.25] * EMBEDDING_DIMENSIONS
            return json.dumps(
                {"data": [{"index": 0, "embedding": vector}]}
            ).encode()[:size]

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        return Response()

    monkeypatch.setattr("app.services.embeddings.urlopen", fake_urlopen)
    settings = Settings(
        embedding_provider="openai_compatible",
        embedding_api_url="https://embedding.example/v1",
        embedding_api_key=SecretStr("test-only-secret"),
    )
    provider = OpenAICompatibleEmbeddingProvider(
        endpoint=settings.embedding_api_url,
        model_name=settings.embedding_model_name,
        model_version=settings.embedding_model_version,
        api_key=settings.embedding_api_key.get_secret_value(),
    )

    vectors = provider.embed(["synthetic test input"])

    assert captured["url"] == "https://embedding.example/v1/embeddings"
    assert captured["authorization"] == "Bearer test-only-secret"
    assert vectors == [[0.25] * EMBEDDING_DIMENSIONS]
