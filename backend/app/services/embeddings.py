import math
import threading
from pathlib import Path
from typing import Optional, Protocol, Sequence

import httpx

from app.core.config import Settings, settings
from app.core.provider_http import post_bounded_json
from app.core.provider_url import validate_provider_url

EMBEDDING_DIMENSIONS = 384
_MAX_PROVIDER_RESPONSE_BYTES = 1_000_000
_LOCAL_PROVIDER_LOCK = threading.Lock()
_LOCAL_PROVIDERS: dict[
    tuple[Path, str],
    "SentenceTransformersEmbeddingProvider",
] = {}


class EmbeddingProvider(Protocol):
    model_name: str
    model_version: str
    dimensions: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class EmbeddingProviderConfigurationError(RuntimeError):
    pass


class EmbeddingProviderError(RuntimeError):
    pass


class SentenceTransformersEmbeddingProvider:
    model_name = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(
        self,
        *,
        model_path: Path,
        model_version: str,
    ) -> None:
        if not model_path.is_dir():
            raise EmbeddingProviderConfigurationError(
                "The local Sentence Transformers model directory does not exist."
            )
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingProviderConfigurationError(
                "Install the optional sentence-transformers package to use local embeddings."
            ) from exc

        try:
            self._model = SentenceTransformer(
                str(model_path),
                local_files_only=True,
                trust_remote_code=False,
            )
            dimensions = self._model.get_sentence_embedding_dimension()
        except Exception as exc:
            raise EmbeddingProviderConfigurationError(
                "The local Sentence Transformers model could not be loaded. "
                "Ensure all model files are present locally."
            ) from exc
        if dimensions != EMBEDDING_DIMENSIONS:
            raise EmbeddingProviderConfigurationError(
                f"The local embedding model must return {EMBEDDING_DIMENSIONS} dimensions."
            )
        self.model_version = model_version
        self.dimensions = EMBEDDING_DIMENSIONS

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = self._model.encode(
                list(texts),
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            if len(vectors) != len(texts):
                raise ValueError("The local model returned an unexpected vector count.")
            return [
                validate_embedding(vector, expected_dimensions=self.dimensions)
                for vector in vectors
            ]
        except (TypeError, ValueError) as exc:
            raise EmbeddingProviderError(
                "The local embedding model returned invalid vectors."
            ) from exc
        except Exception as exc:
            raise EmbeddingProviderError(
                "The local embedding model failed to encode the input."
            ) from exc


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        endpoint: str,
        model_name: str,
        model_version: str,
        api_key: Optional[str],
        timeout_seconds: float = 60,
    ) -> None:
        try:
            validate_provider_url(endpoint, has_api_key=bool(api_key))
        except ValueError as exc:
            raise EmbeddingProviderConfigurationError(
                "The embedding provider URL is invalid or insecure."
            ) from exc
        self.endpoint = endpoint.rstrip("/")
        self.model_name = model_name
        self.model_version = model_version
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.dimensions = EMBEDDING_DIMENSIONS

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            payload = post_bounded_json(
                f"{self.endpoint}/embeddings",
                payload={"model": self.model_name, "input": list(texts), "dimensions": self.dimensions},
                headers=headers,
                timeout=self.timeout_seconds,
                max_response_bytes=_MAX_PROVIDER_RESPONSE_BYTES,
            )
        except (
            httpx.HTTPError,
            httpx.TimeoutException,
            ValueError,
            TypeError,
            OSError,
        ) as exc:
            raise EmbeddingProviderError(
                "The configured embedding provider request failed."
            ) from exc

        try:
            data = payload["data"]
            vectors = [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
        except (KeyError, TypeError, IndexError) as exc:
            raise EmbeddingProviderError(
                "The embedding provider returned an invalid response."
            ) from exc
        if len(vectors) != len(texts):
            raise EmbeddingProviderError(
                "The embedding provider returned an unexpected number of vectors."
            )
        return [
            validate_embedding(vector, expected_dimensions=self.dimensions)
            for vector in vectors
        ]


def validate_embedding(
    vector: Sequence[float],
    *,
    expected_dimensions: int = EMBEDDING_DIMENSIONS,
) -> list[float]:
    try:
        vector_length = len(vector)
    except TypeError as exc:
        raise ValueError("Embedding must be a numeric sequence.") from exc
    if vector_length != expected_dimensions:
        raise ValueError(
            f"Expected an embedding of {expected_dimensions} dimensions, got {vector_length}."
        )
    try:
        normalized = [float(value) for value in vector]
    except (TypeError, ValueError) as exc:
        raise ValueError("Embedding values must be numbers.") from exc
    if not all(math.isfinite(value) for value in normalized):
        raise ValueError("Embedding values must be finite numbers.")
    return normalized


def get_embedding_provider(
    configured_settings: Settings = settings,
) -> Optional[EmbeddingProvider]:
    if configured_settings.embedding_provider == "disabled":
        return None
    if configured_settings.embedding_provider == "openai_compatible":
        if not configured_settings.embedding_api_url:
            raise EmbeddingProviderConfigurationError(
                "EMBEDDING_API_URL is required for the openai_compatible provider."
            )
        api_key = (
            configured_settings.embedding_api_key.get_secret_value()
            if configured_settings.embedding_api_key
            else None
        )
        return OpenAICompatibleEmbeddingProvider(
            endpoint=configured_settings.embedding_api_url,
            model_name=configured_settings.embedding_model_name,
            model_version=configured_settings.embedding_model_version,
            api_key=api_key,
        )
    if configured_settings.embedding_provider == "sentence_transformers":
        if configured_settings.embedding_local_model_path is None:
            raise EmbeddingProviderConfigurationError(
                "EMBEDDING_LOCAL_MODEL_PATH is required for sentence_transformers."
            )
        model_path = configured_settings.embedding_local_model_path
        model_version = configured_settings.embedding_model_version
        provider_key = (model_path.resolve(), model_version)
        with _LOCAL_PROVIDER_LOCK:
            provider = _LOCAL_PROVIDERS.get(provider_key)
            if provider is None:
                provider = SentenceTransformersEmbeddingProvider(
                    model_path=model_path,
                    model_version=model_version,
                )
                _LOCAL_PROVIDERS[provider_key] = provider
        return provider
    raise EmbeddingProviderConfigurationError(
        "The configured embedding provider is not supported."
    )
