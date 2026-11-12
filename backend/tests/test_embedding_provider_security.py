import builtins
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services.embeddings import (
    EMBEDDING_DIMENSIONS,
    EmbeddingProviderConfigurationError,
    EmbeddingProviderError,
    OpenAICompatibleEmbeddingProvider,
    SentenceTransformersEmbeddingProvider,
    get_embedding_provider,
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
        "http://embedding.example/v1",
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


def test_embedding_provider_bounds_response_size_and_sets_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {"bytes": 0}

    class OversizedResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self, chunk_size: int):
            while captured["bytes"] < 2_000_000:
                captured["bytes"] += chunk_size
                yield b" " * chunk_size

    def fake_stream(method, url, **kwargs):
        captured["url"] = url
        captured["timeout"] = kwargs["timeout"]
        captured["method"] = method
        return OversizedResponse()

    monkeypatch.setattr("app.services.embeddings.httpx.stream", fake_stream)
    provider = OpenAICompatibleEmbeddingProvider(
        endpoint="https://embedding.example/v1",
        model_name="test-model",
        model_version="test-v1",
        api_key=None,
    )

    with pytest.raises(EmbeddingProviderError, match="request failed"):
        provider.embed(["synthetic test input"])

    assert captured["method"] == "POST"
    assert captured["url"] == "https://embedding.example/v1/embeddings"
    assert captured["bytes"] <= 1_000_000 + 64 * 1024
    assert captured["timeout"] > 0


def test_embedding_provider_sends_key_only_to_https(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self, chunk_size: int):
            vector = [0.25] * EMBEDDING_DIMENSIONS
            yield json.dumps(
                {"data": [{"index": 0, "embedding": vector}]}
            ).encode()

    def fake_stream(method, url, **kwargs):
        captured["url"] = url
        captured["authorization"] = kwargs["headers"].get("Authorization")
        captured["timeout"] = kwargs["timeout"]
        return Response()

    monkeypatch.setattr("app.services.embeddings.httpx.stream", fake_stream)
    configured = Settings(
        embedding_provider="openai_compatible",
        embedding_api_url="https://embedding.example/v1",
        embedding_api_key=SecretStr("test-only-secret"),
    )
    provider = OpenAICompatibleEmbeddingProvider(
        endpoint=configured.embedding_api_url,
        model_name=configured.embedding_model_name,
        model_version=configured.embedding_model_version,
        api_key=configured.embedding_api_key.get_secret_value(),
    )

    vectors = provider.embed(["synthetic test input"])

    assert captured["url"] == "https://embedding.example/v1/embeddings"
    assert captured["authorization"] == "Bearer test-only-secret"
    assert captured["timeout"] > 0
    assert vectors == [[0.25] * EMBEDDING_DIMENSIONS]


def test_local_sentence_transformer_requires_existing_model_files(tmp_path) -> None:
    with pytest.raises(
        EmbeddingProviderConfigurationError,
        match="directory does not exist",
    ):
        SentenceTransformersEmbeddingProvider(
            model_path=tmp_path / "missing-model",
            model_version="synthetic-v1",
        )


def test_empty_local_model_path_is_treated_as_unset() -> None:
    assert Settings(embedding_local_model_path="").embedding_local_model_path is None


def test_local_sentence_transformer_requires_optional_package(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    model_path = tmp_path / "model"
    model_path.mkdir()
    original_import = builtins.__import__

    def import_without_sentence_transformers(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_sentence_transformers)
    with pytest.raises(
        EmbeddingProviderConfigurationError,
        match="optional sentence-transformers package",
    ):
        SentenceTransformersEmbeddingProvider(
            model_path=model_path,
            model_version="synthetic-v1",
        )


def test_local_sentence_transformer_loads_only_local_384_dimension_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    model_path = tmp_path / "local-model"
    model_path.mkdir()
    captured = {}

    class FakeModel:
        def get_sentence_embedding_dimension(self):
            return EMBEDDING_DIMENSIONS

        def encode(self, texts, **kwargs):
            captured["texts"] = texts
            captured["encode_options"] = kwargs
            return [[0.5] * EMBEDDING_DIMENSIONS for _ in texts]

    def fake_constructor(path, **kwargs):
        captured["path"] = path
        captured["load_options"] = kwargs
        return FakeModel()

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=fake_constructor),
    )
    provider = SentenceTransformersEmbeddingProvider(
        model_path=model_path,
        model_version="synthetic-v1",
    )

    assert provider.embed(["synthetic fixture"]) == [
        [0.5] * EMBEDDING_DIMENSIONS
    ]
    assert captured["path"] == str(model_path)
    assert captured["load_options"]["local_files_only"] is True
    assert captured["load_options"]["trust_remote_code"] is False
    assert captured["encode_options"]["show_progress_bar"] is False


def test_concurrent_local_provider_requests_share_one_model_load(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    model_path = tmp_path / "concurrent-local-model"
    model_path.mkdir()
    constructor_calls = 0
    constructor_lock = threading.Lock()

    class FakeModel:
        def get_sentence_embedding_dimension(self):
            return EMBEDDING_DIMENSIONS

        def encode(self, texts, **kwargs):
            return [[0.5] * EMBEDDING_DIMENSIONS for _ in texts]

    def fake_constructor(path, **kwargs):
        nonlocal constructor_calls
        with constructor_lock:
            constructor_calls += 1
        return FakeModel()

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=fake_constructor),
    )
    configured = Settings(
        embedding_provider="sentence_transformers",
        embedding_local_model_path=model_path,
        embedding_model_version="concurrent-test-v1",
    )
    start = threading.Barrier(8)

    def get_provider():
        start.wait()
        return get_embedding_provider(configured)

    with ThreadPoolExecutor(max_workers=8) as executor:
        providers = list(executor.map(lambda _: get_provider(), range(8)))

    assert constructor_calls == 1
    assert all(provider is providers[0] for provider in providers)


def test_local_sentence_transformer_rejects_incompatible_vector_dimension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    model_path = tmp_path / "local-model"
    model_path.mkdir()
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(
            SentenceTransformer=lambda *args, **kwargs: SimpleNamespace(
                get_sentence_embedding_dimension=lambda: 768
            )
        ),
    )

    with pytest.raises(EmbeddingProviderConfigurationError, match="384 dimensions"):
        SentenceTransformersEmbeddingProvider(
            model_path=model_path,
            model_version="synthetic-v1",
        )
