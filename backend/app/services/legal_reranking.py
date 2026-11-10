import logging
from pathlib import Path
from threading import Lock
from typing import Optional, Protocol

from app.core.config import Settings, get_settings
from app.schemas.legal_retrieval import LegalEvidenceResult

logger = logging.getLogger(__name__)


class LegalEvidenceReranker(Protocol):
    def rerank(
        self,
        query: str,
        results: list[LegalEvidenceResult],
    ) -> list[LegalEvidenceResult]: ...


class CrossEncoderLegalEvidenceReranker:
    def __init__(self, model_path: Path) -> None:
        if not model_path.is_dir():
            raise FileNotFoundError(
                f"Cross-encoder model directory does not exist: {model_path}"
            )
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional sentence-transformers package to use reranking."
            ) from exc

        self._model = CrossEncoder(
            str(model_path),
            model_kwargs={"local_files_only": True, "trust_remote_code": False},
            tokenizer_kwargs={"local_files_only": True},
        )

    def rerank(
        self,
        query: str,
        results: list[LegalEvidenceResult],
    ) -> list[LegalEvidenceResult]:
        if not results:
            return []
        scores = self._model.predict([(query, result.text) for result in results])
        if len(scores) != len(results):
            raise ValueError("Cross-encoder returned an unexpected score count.")
        return [
            result
            for _, result in sorted(
                zip(scores, results),
                key=lambda item: float(item[0]),
                reverse=True,
            )
        ]


_reranker_instances: dict[tuple[str, str], Optional[LegalEvidenceReranker]] = {}
_reranker_lock = Lock()


def get_legal_evidence_reranker(
    settings: Optional[Settings] = None,
) -> Optional[LegalEvidenceReranker]:
    current_settings = settings or get_settings()
    model_path = current_settings.legal_reranker_model_path
    if not current_settings.legal_reranker_enabled or model_path is None:
        return None

    resolved_path = model_path.expanduser().resolve()
    cache_key = (str(resolved_path), current_settings.legal_reranker_model_version)
    with _reranker_lock:
        if cache_key in _reranker_instances:
            return _reranker_instances[cache_key]
        try:
            reranker: Optional[LegalEvidenceReranker] = (
                CrossEncoderLegalEvidenceReranker(Path(cache_key[0]))
            )
        except Exception as exc:
            logger.warning(
                "Cross-encoder reranking is unavailable; using fused retrieval order",
                extra={
                    "model_path": str(resolved_path),
                    "error_type": type(exc).__name__,
                },
            )
            reranker = None
        _reranker_instances[cache_key] = reranker
        return reranker
