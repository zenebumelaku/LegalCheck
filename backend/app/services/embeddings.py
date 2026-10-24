import json
import math
from typing import Optional, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings, settings

EMBEDDING_DIMENSIONS = 384


class EmbeddingProvider(Protocol):
    model_name: str
    model_version: str
    dimensions: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class EmbeddingProviderConfigurationError(RuntimeError):
    pass


class EmbeddingProviderError(RuntimeError):
    pass


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
        self.endpoint = endpoint.rstrip("/")
        self.model_name = model_name
        self.model_version = model_version
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.dimensions = EMBEDDING_DIMENSIONS

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        request_body = json.dumps(
            {
                "model": self.model_name,
                "input": list(texts),
                "dimensions": self.dimensions,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            f"{self.endpoint}/embeddings",
            data=request_body,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
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
    raise EmbeddingProviderConfigurationError(
        "The configured embedding provider is not supported."
    )
