import os
from uuid import uuid4

import pytest
from redis import Redis

from app.core.config import Settings
from app.schemas.legal_questions import LegalQuestionAnswer, LegalQuestionCitation
from app.services.legal_question_cache import RedisLegalQuestionCache

pytestmark = pytest.mark.skipif(
    os.getenv("LEGAL_QA_REDIS_INTEGRATION") != "1",
    reason="Set LEGAL_QA_REDIS_INTEGRATION=1 to test against a real Redis server.",
)


def test_real_redis_cache_round_trip_and_ttl() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = Redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()
    cache = RedisLegalQuestionCache(Settings(redis_url=redis_url))
    key = f"legalcheck:integration-test:{uuid4()}"
    answer = LegalQuestionAnswer(
        status="answered",
        question="Synthetic integration fixture question?",
        answer="Synthetic integration fixture answer.",
        review_date="2026-01-01",
        citations=[
            LegalQuestionCitation(
                source_id=uuid4(),
                source_title="Synthetic test fixture; not legal evidence",
                source_version_label="synthetic-fixture-v1",
                law_number="SYNTHETIC-ONLY",
                source_url="https://example.test/synthetic",
                provision_id=uuid4(),
                article_number="fixture",
                sub_article_reference=None,
                page_number=1,
                supporting_quote="Synthetic fixture quote.",
            )
        ],
        model_name="synthetic-integration-test-model",
        model_version="fixture-v1",
    )
    try:
        cache.set(key, answer, 30)

        cached = cache.get(key)

        assert cached == answer
        assert 0 < redis_client.ttl(key) <= 30
    finally:
        redis_client.delete(key)
        redis_client.close()
