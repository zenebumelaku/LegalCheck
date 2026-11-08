import hashlib
import json
import logging
import unicodedata
from functools import lru_cache
from typing import Optional, Protocol

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import LegalProvision, LegalProvisionChunk, LegalSource
from app.schemas.legal_questions import LegalQuestionAnswer

logger = logging.getLogger(__name__)

LEGAL_QUESTION_PROMPT_VERSION = "v1"
_CACHE_KEY_PREFIX = "legalcheck:legal-qa"


class LegalQuestionCache(Protocol):
    def get(self, key: str) -> Optional[LegalQuestionAnswer]: ...

    def set(
        self,
        key: str,
        answer: LegalQuestionAnswer,
        ttl_seconds: int,
    ) -> None: ...


class RedisLegalQuestionCache:
    def __init__(self, settings: Settings) -> None:
        self._redis = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )

    def get(self, key: str) -> Optional[LegalQuestionAnswer]:
        value = self._redis.get(key)
        if value is None:
            return None
        try:
            answer = LegalQuestionAnswer.model_validate_json(value)
        except (ValueError, TypeError) as exc:
            logger.warning(
                "Discarding invalid legal-question cache entry",
                extra={"error_type": type(exc).__name__},
            )
            try:
                self._redis.delete(key)
            except RedisError:
                logger.warning("Could not remove invalid legal-question cache entry")
            return None
        if answer.status != "answered" or not answer.citations:
            logger.warning("Discarding unsupported legal-question cache entry")
            try:
                self._redis.delete(key)
            except RedisError:
                logger.warning("Could not remove unsupported legal-question cache entry")
            return None
        return answer

    def set(
        self,
        key: str,
        answer: LegalQuestionAnswer,
        ttl_seconds: int,
    ) -> None:
        if answer.status != "answered" or not answer.citations:
            raise ValueError("Only supported legal-question answers may be cached.")
        if ttl_seconds > 0:
            self._redis.setex(
                key,
                ttl_seconds,
                answer.model_copy(update={"cache_hit": False}).model_dump_json(),
            )


def normalize_legal_question(question: str) -> str:
    normalized = unicodedata.normalize("NFC", question)
    return " ".join(normalized.split())


def legal_knowledge_base_version(db: Session) -> str:
    statement = (
        select(
            LegalSource.id,
            LegalSource.title,
            LegalSource.law_number,
            LegalSource.source_type,
            LegalSource.jurisdiction,
            LegalSource.language,
            LegalSource.publication_date,
            LegalSource.effective_date,
            LegalSource.end_date,
            LegalSource.legal_status,
            LegalSource.version_label,
            LegalSource.original_source_url,
            LegalSource.file_checksum,
            LegalSource.verification_status,
            LegalSource.verified_at,
            LegalSource.verified_by,
            LegalSource.updated_at,
            LegalProvision.id,
            LegalProvision.article_number,
            LegalProvision.sub_article_reference,
            LegalProvision.section_title,
            LegalProvision.text,
            LegalProvision.page_number,
            LegalProvision.language,
            LegalProvisionChunk.id,
            LegalProvisionChunk.chunk_index,
            LegalProvisionChunk.chunk_text,
            LegalProvisionChunk.content_checksum,
            LegalProvisionChunk.page_number,
            LegalProvisionChunk.source_version_label,
            LegalProvisionChunk.embedding_model,
            LegalProvisionChunk.embedding_version,
            LegalProvisionChunk.embedding.is_not(None),
            LegalProvisionChunk.created_at,
        )
        .select_from(LegalSource)
        .outerjoin(
            LegalProvision,
            LegalProvision.legal_source_id == LegalSource.id,
        )
        .outerjoin(
            LegalProvisionChunk,
            LegalProvisionChunk.provision_id == LegalProvision.id,
        )
        .order_by(
            LegalSource.id,
            LegalProvision.id,
            LegalProvisionChunk.id,
        )
    )
    digest = hashlib.sha256()
    for row in db.execute(statement):
        digest.update(
            json.dumps(
                [str(value) if value is not None else None for value in row],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def legal_question_cache_key(
    *,
    question: str,
    context: dict,
    knowledge_base_version: str,
    settings: Settings,
) -> str:
    key_material = {
        "cache_version": settings.legal_qa_cache_version,
        "prompt_version": LEGAL_QUESTION_PROMPT_VERSION,
        "question": normalize_legal_question(question),
        "review_context": context,
        "knowledge_base_version": knowledge_base_version,
        "llm_provider": settings.llm_provider,
        "llm_api_url": settings.llm_api_url,
        "llm_model_name": settings.llm_model_name,
        "llm_model_version": settings.llm_model_version,
        "embedding_provider": settings.embedding_provider,
        "embedding_api_url": settings.embedding_api_url,
        "embedding_model_name": settings.embedding_model_name,
        "embedding_model_version": settings.embedding_model_version,
    }
    digest = hashlib.sha256(
        json.dumps(
            key_material,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"{_CACHE_KEY_PREFIX}:{settings.legal_qa_cache_version}:{digest}"


@lru_cache
def get_legal_question_cache() -> LegalQuestionCache:
    return RedisLegalQuestionCache(get_settings())
