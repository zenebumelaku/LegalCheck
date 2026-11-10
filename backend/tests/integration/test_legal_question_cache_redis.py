import json
import os
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from redis import Redis
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import LegalProvision, LegalSource
from app.db.session import get_db
from app.main import app
from app.schemas.legal_questions import LegalQuestionAnswer, LegalQuestionCitation
from app.services.legal_question_cache import (
    RedisLegalQuestionCache,
    legal_question_cache_key as build_cache_key,
)
import app.services.legal_question_answering as legal_question_answering
import app.services.legal_retrieval as legal_retrieval

pytestmark = [
    pytest.mark.redis_integration,
    pytest.mark.skipif(
        os.getenv("LEGAL_QA_REDIS_INTEGRATION") != "1",
        reason="Set LEGAL_QA_REDIS_INTEGRATION=1 to test against a real Redis server.",
    ),
]


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


def test_real_redis_cache_aside_request_hit_and_knowledge_base_invalidation(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = Redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()
    cache = RedisLegalQuestionCache(Settings(redis_url=redis_url))
    cache_keys: list[str] = []
    original_key_builder = build_cache_key
    unique_question = f"How often does synthetic fixture {uuid4().hex} say wages are paid?"

    def track_cache_key(**kwargs):
        key = original_key_builder(**kwargs)
        cache_keys.append(key)
        return key

    class SyntheticIntegrationProvider:
        model_name = "synthetic-integration-provider"
        model_version = "fixture-v1"

        def __init__(self) -> None:
            self.calls: list[tuple[str, list[dict]]] = []

        def answer_legal_question(self, question: str, evidence: list[dict]) -> str:
            self.calls.append((question, evidence))
            selected = evidence[0]
            return json.dumps(
                {
                    "answer": (
                        "Synthetic test fixture only: wages are paid monthly."
                    ),
                    "evidence_assessment": "supporting",
                    "citations": [
                        {
                            "source_id": selected["source_id"],
                            "provision_id": selected["provision_id"],
                            "article_number": selected["article_number"],
                            "sub_article_reference": selected[
                                "sub_article_reference"
                            ],
                            "supporting_quote": (
                                "Synthetic fixture clause: wages are paid monthly."
                            ),
                        }
                    ],
                }
            )

    provider = SyntheticIntegrationProvider()
    retrieval_calls = 0
    original_retrieval = legal_question_answering.retrieve_legal_evidence

    def counted_retrieval(*args, **kwargs):
        nonlocal retrieval_calls
        retrieval_calls += 1
        return original_retrieval(*args, **kwargs)

    def override_get_db():
        yield db_session

    monkeypatch.setattr(
        legal_question_answering,
        "get_settings",
        lambda: Settings(
            redis_url=redis_url,
            legal_qa_cache_ttl_seconds=60,
            legal_qa_cache_version="redis-integration-v1",
        ),
    )
    monkeypatch.setattr(
        legal_question_answering,
        "get_legal_question_cache",
        lambda *args, **kwargs: cache,
    )
    monkeypatch.setattr(
        legal_question_answering,
        "get_llm_provider",
        lambda *args, **kwargs: provider,
    )
    monkeypatch.setattr(
        legal_question_answering,
        "legal_question_cache_key",
        track_cache_key,
    )
    monkeypatch.setattr(
        legal_question_answering,
        "retrieve_legal_evidence",
        counted_retrieval,
    )
    monkeypatch.setattr(
        legal_retrieval,
        "get_embedding_provider",
        lambda *args, **kwargs: None,
    )
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            registered = client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Redis Integration Test",
                    "email": f"{uuid4().hex}@example.com",
                    "password": "a-long-redis-integration-password",
                },
            )
            assert registered.status_code == 201
            logged_in = client.post(
                "/api/v1/auth/login",
                json={
                    "email": registered.json()["email"],
                    "password": "a-long-redis-integration-password",
                },
            )
            assert logged_in.status_code == 200
            token = logged_in.json()["access_token"]
            user_id = UUID(registered.json()["id"])

            source = LegalSource(
                title="Synthetic Redis integration fixture; not legal evidence",
                law_number=f"SYNTHETIC-REDIS-{uuid4().hex}",
                source_type="test_fixture",
                jurisdiction="ET",
                language="en",
                effective_date=date(2020, 1, 1),
                legal_status="current",
                version_label="synthetic-integration-v1",
                original_source_url="https://example.test/redis-fixture.pdf",
                file_checksum=uuid4().hex * 2,
                source_file_storage_key=f"test-fixtures/{uuid4()}.pdf",
                verification_status="verified",
                verified_by=user_id,
                verified_at=datetime.now(timezone.utc),
            )
            provision = LegalProvision(
                legal_source=source,
                article_number="synthetic-article-1",
                sub_article_reference="synthetic-subarticle-1",
                section_title="Synthetic test fixture clause",
                text="Synthetic fixture clause: wages are paid monthly.",
                page_number=1,
                language="en",
            )
            db_session.add(provision)
            db_session.commit()

            headers = {"Authorization": f"Bearer {token}"}
            request_body = {
                "question": unique_question,
                "review_context": {
                    "review_date": "2024-01-01",
                    "jurisdiction": "ET",
                    "language": "en",
                },
            }
            first = client.post(
                "/api/v1/legal-questions/answer",
                headers=headers,
                json=request_body,
            )
            equivalent = client.post(
                "/api/v1/legal-questions/answer",
                headers=headers,
                json={
                    **request_body,
                    "question": f"  {unique_question}  ",
                },
            )

            assert first.status_code == equivalent.status_code == 200
            first_payload = first.json()
            equivalent_payload = equivalent.json()
            assert first_payload["cache_hit"] is False
            assert equivalent_payload["cache_hit"] is True
            assert equivalent_payload["answer"] == first_payload["answer"]
            assert equivalent_payload["citations"] == first_payload["citations"]
            assert retrieval_calls == 1
            assert len(provider.calls) == 1

            source.title = "Updated synthetic Redis integration fixture"
            db_session.commit()
            after_version_change = client.post(
                "/api/v1/legal-questions/answer",
                headers=headers,
                json=request_body,
            )

            assert after_version_change.status_code == 200
            assert after_version_change.json()["cache_hit"] is False
            assert retrieval_calls == 2
            assert len(provider.calls) == 2
            assert len(set(cache_keys)) == 2
    finally:
        app.dependency_overrides.pop(get_db, None)
        if cache_keys:
            redis_client.delete(*cache_keys)
        redis_client.close()
