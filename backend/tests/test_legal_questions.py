import json
from datetime import date, datetime, timezone
from typing import Generator, Optional
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import (
    LegalProvision,
    LegalProvisionChunk,
    LegalQuestionConversation,
    LegalQuestionMessage,
    LegalSource,
)
from app.db.session import get_db
from app.main import app
from app.schemas.legal_questions import LegalQuestionAnswer
from app.services.legal_question_cache import (
    legal_question_cache_key,
    legal_question_cache_metrics,
)
from app.services.llm_provider import LLMProviderError, LLMProviderRateLimitError
import app.services.legal_question_answering as legal_question_answering

pytestmark = pytest.mark.unit


class MemoryAnswerCache:
    def __init__(self) -> None:
        self.entries: dict[str, LegalQuestionAnswer] = {}
        self.get_calls: list[str] = []
        self.set_calls: list[str] = []
        self.fail_get = False
        self.fail_set = False

    def get(self, key: str) -> Optional[LegalQuestionAnswer]:
        self.get_calls.append(key)
        if self.fail_get:
            raise RedisConnectionError("synthetic Redis outage")
        return self.entries.get(key)

    def set(
        self,
        key: str,
        answer: LegalQuestionAnswer,
        ttl_seconds: int,
    ) -> None:
        self.set_calls.append(key)
        if self.fail_set:
            raise RedisConnectionError("synthetic Redis outage")
        self.entries[key] = answer


class MockQuestionProvider:
    model_name = "synthetic-question-provider"
    model_version = "fixture-v1"

    def __init__(self, response: Optional[dict] = None) -> None:
        self.response = response or {}
        self.calls: list[tuple[str, list[dict]]] = []

    def answer_legal_question(self, question: str, evidence: list[dict]) -> str:
        self.calls.append((question, evidence))
        return json.dumps(self.response)


@pytest.fixture
def answer_cache() -> MemoryAnswerCache:
    return MemoryAnswerCache()


@pytest.fixture
def legal_question_client(
    db_session: Session,
    answer_cache: MemoryAnswerCache,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_legal_question_cache",
        lambda: answer_cache,
    )
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _login(client: TestClient) -> tuple[UUID, str]:
    email = f"{uuid4()}@example.com"
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Legal Question Test User",
            "email": email,
            "password": "a-long-legal-question-test-password",
        },
    )
    assert registered.status_code == 201
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "a-long-legal-question-test-password",
        },
    )
    assert login_response.status_code == 200
    return UUID(registered.json()["id"]), login_response.json()["access_token"]


def _add_source(
    db: Session,
    *,
    user_id: UUID,
    verified: bool = True,
    legal_status: str = "current",
    effective_date: date = date(2020, 1, 1),
    text: str = "Synthetic fixture rule: wages are paid monthly.",
) -> LegalProvision:
    source_token = uuid4().hex
    source = LegalSource(
        title="Synthetic fixture source; not legal evidence",
        law_number=f"SYNTHETIC-QUESTION-{source_token}",
        source_type="test_fixture",
        jurisdiction="ET",
        language="en",
        effective_date=effective_date,
        legal_status=legal_status,
        version_label=f"synthetic-{source_token}",
        original_source_url="https://example.test/synthetic-fixture.pdf",
        file_checksum=uuid4().hex * 2,
        source_file_storage_key=f"test-fixtures/{uuid4()}.pdf",
        verification_status="verified" if verified else "pending",
        verified_by=user_id if verified else None,
        verified_at=datetime.now(timezone.utc) if verified else None,
    )
    provision = LegalProvision(
        legal_source=source,
        article_number="fixture-article-1",
        sub_article_reference="fixture-sub-1",
        section_title="Synthetic fixture heading",
        text=text,
        page_number=9,
        language="en",
    )
    db.add(provision)
    db.commit()
    db.refresh(provision)
    return provision


def _supported_response(provision: LegalProvision, **overrides) -> dict:
    citation = {
        "source_id": str(provision.legal_source.id),
        "provision_id": str(provision.id),
        "article_number": provision.article_number,
        "sub_article_reference": provision.sub_article_reference,
        "supporting_quote": "Synthetic fixture rule: wages are paid monthly.",
    }
    citation.update(overrides.pop("citation", {}))
    return {
        "answer": "The synthetic fixture states that wages are paid monthly.",
        "evidence_assessment": "supporting",
        "citations": [citation],
        **overrides,
    }


def _ask(
    client: TestClient,
    token: str,
    *,
    question: str = "What does the synthetic fixture say about wages?",
) -> object:
    return client.post(
        "/api/v1/legal-questions/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question": question,
            "review_context": {
                "review_date": "2024-01-01",
                "jurisdiction": "ET",
                "language": "en",
            },
        },
    )


def _ask_in_conversation(
    client: TestClient,
    token: str,
    *,
    question: str = "What does the synthetic fixture say about wages?",
    conversation_id: Optional[str] = None,
) -> object:
    return client.post(
        "/api/v1/legal-questions/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question": question,
            "conversation_id": conversation_id,
            "review_context": {
                "review_date": "2024-01-01",
                "jurisdiction": "ET",
                "language": "en",
            },
        },
    )


@pytest.mark.parametrize(
    "verified,legal_status,effective_date",
    [
        (False, "current", date(2020, 1, 1)),
        (True, "unknown", date(2020, 1, 1)),
        (True, "current", date(2025, 1, 1)),
    ],
)
def test_no_eligible_evidence_returns_insufficient_without_provider(
    legal_question_client: TestClient,
    answer_cache: MemoryAnswerCache,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    verified: bool,
    legal_status: str,
    effective_date: date,
) -> None:
    user_id, token = _login(legal_question_client)
    _add_source(
        db_session,
        user_id=user_id,
        verified=verified,
        legal_status=legal_status,
        effective_date=effective_date,
    )

    def unavailable_provider(*args, **kwargs):
        raise AssertionError("Provider must not be called without eligible evidence.")

    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        unavailable_provider,
    )
    response = _ask(legal_question_client, token)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_evidence"
    assert payload["citations"] == []
    assert payload["model_name"] is None
    assert answer_cache.set_calls == []


def test_eligible_retrieved_evidence_is_answered_and_cited(
    legal_question_client: TestClient,
    answer_cache: MemoryAnswerCache,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )

    response = _ask(legal_question_client, token)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    assert payload["answer"] == "The synthetic fixture states that wages are paid monthly."
    assert payload["citations"][0]["source_id"] == str(provision.legal_source.id)
    assert payload["citations"][0]["article_number"] == provision.article_number
    assert payload["citations"][0]["sub_article_reference"] == provision.sub_article_reference
    assert payload["citations"][0]["page_number"] == 9
    assert "not legal advice" in payload["disclaimer"]
    assert payload["cache_hit"] is False
    assert provider.calls[0][1][0]["provision_id"] == str(provision.id)
    assert answer_cache.set_calls


def test_second_normalized_question_hits_cache_before_retrieval_or_generation(
    legal_question_client: TestClient,
    answer_cache: MemoryAnswerCache,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics_before = legal_question_cache_metrics.snapshot()
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )
    original_retrieval = legal_question_answering.retrieve_legal_evidence
    retrieval_calls = 0

    def counted_retrieval(*args, **kwargs):
        nonlocal retrieval_calls
        retrieval_calls += 1
        return original_retrieval(*args, **kwargs)

    monkeypatch.setattr(
        "app.services.legal_question_answering.retrieve_legal_evidence",
        counted_retrieval,
    )
    first = _ask(legal_question_client, token)
    second = _ask(
        legal_question_client,
        token,
        question="  What does the synthetic fixture say about wages? \n",
    )

    assert first.status_code == second.status_code == 200
    first_payload, second_payload = first.json(), second.json()
    assert first_payload["cache_hit"] is False
    assert second_payload["cache_hit"] is True
    assert second_payload["answer"] == first_payload["answer"]
    assert second_payload["citations"] == first_payload["citations"]
    assert retrieval_calls == 1
    assert len(provider.calls) == 1
    assert len(answer_cache.get_calls) == 2
    assert answer_cache.get_calls[0] == answer_cache.get_calls[1]
    metrics_after = legal_question_cache_metrics.snapshot()
    assert metrics_after["hits"] - metrics_before["hits"] == 1
    assert metrics_after["misses"] - metrics_before["misses"] == 1
    assert metrics_after["provider_calls"] - metrics_before["provider_calls"] == 1
    assert (
        metrics_after["provider_calls_avoided"]
        - metrics_before["provider_calls_avoided"]
        == 1
    )


@pytest.mark.parametrize("change_kind", ["source_change", "reindex"])
def test_knowledge_base_changes_invalidate_previous_answer(
    legal_question_client: TestClient,
    answer_cache: MemoryAnswerCache,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    change_kind: str,
) -> None:
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )
    first = _ask(legal_question_client, token)
    assert first.status_code == 200 and first.json()["cache_hit"] is False
    metrics_before_change = legal_question_cache_metrics.snapshot()

    if change_kind == "source_change":
        provision.legal_source.title = "Updated synthetic fixture source"
    else:
        db_session.add(
            LegalProvisionChunk(
                provision_id=provision.id,
                chunk_index=0,
                chunk_text=provision.text,
                content_checksum="b" * 64,
                page_number=provision.page_number,
                source_version_label=provision.legal_source.version_label,
                embedding_model="synthetic-reindex-model",
                embedding_version="synthetic-v1",
            )
        )
    db_session.commit()
    second = _ask(legal_question_client, token)

    assert second.status_code == 200
    assert second.json()["cache_hit"] is False
    assert len(provider.calls) == 2
    assert answer_cache.get_calls[0] != answer_cache.get_calls[1]
    metrics_after_change = legal_question_cache_metrics.snapshot()
    assert (
        metrics_after_change["logical_invalidations"]
        - metrics_before_change["logical_invalidations"]
        == 1
    )


def test_cache_key_includes_explicit_cache_version_and_normalizes_question() -> None:
    settings_v1 = Settings(legal_qa_cache_version="v1")
    settings_v2 = Settings(legal_qa_cache_version="v2")
    common = {
        "context": {"jurisdiction": "ET", "review_date": "2024-01-01"},
        "knowledge_base_version": "synthetic-kb-v1",
    }

    first_key = legal_question_cache_key(
        question="What   is the rule?",
        settings=settings_v1,
        **common,
    )
    normalized_key = legal_question_cache_key(
        question=" What is the rule? ",
        settings=settings_v1,
        **common,
    )
    next_version_key = legal_question_cache_key(
        question="What is the rule?",
        settings=settings_v2,
        **common,
    )

    assert first_key == normalized_key
    assert first_key != next_version_key


def test_cache_key_includes_effective_legal_qa_provider() -> None:
    common = {
        "question": "What is the rule?",
        "context": {"jurisdiction": "ET", "review_date": "2024-01-01"},
        "knowledge_base_version": "synthetic-kb-v1",
    }
    audit_provider_disabled = Settings(llm_provider="disabled")
    qa_provider_gemini = Settings(
        llm_provider="disabled",
        legal_qa_llm_provider="gemini",
    )

    disabled_key = legal_question_cache_key(
        settings=audit_provider_disabled,
        **common,
    )
    gemini_key = legal_question_cache_key(
        settings=qa_provider_gemini,
        **common,
    )

    assert disabled_key != gemini_key


def test_conversation_create_continue_and_read_preserves_citation_snapshot(
    legal_question_client: TestClient,
    answer_cache: MemoryAnswerCache,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )

    created = _ask_in_conversation(
        legal_question_client,
        token,
        question="What does the fixture say about wages?",
    )
    assert created.status_code == 201
    conversation_id = created.json()["conversation_id"]
    citation_snapshot = created.json()["answer"]["citations"][0]

    continued = _ask_in_conversation(
        legal_question_client,
        token,
        question="Can you clarify that wage rule?",
        conversation_id=conversation_id,
    )
    assert continued.status_code == 200
    assert "Prior conversation turns" in provider.calls[1][0]
    assert "What does the fixture say about wages?" in provider.calls[1][0]

    provision.legal_source.title = "Updated synthetic source title"
    provision.legal_source.version_label = "updated-synthetic-version"
    provision.text = "Updated synthetic content; not the historical fixture."
    db_session.commit()
    history = legal_question_client.get(
        f"/api/v1/legal-questions/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert history.status_code == 200
    messages = history.json()["messages"]
    assert [message["role"] for message in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[1]["citations"][0] == citation_snapshot
    assert (
        messages[1]["citations"][0]["source_title"]
        == "Synthetic fixture source; not legal evidence"
    )
    assert messages[1]["citations"][0]["source_version_label"].startswith(
        "synthetic-"
    )
    assert messages[1]["content"] == _supported_response(provision)["answer"]


def test_conversation_list_is_owned_and_paginated(
    legal_question_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id, owner_token = _login(legal_question_client)
    _, other_token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=owner_id)
    provider = MockQuestionProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )
    conversation_ids = []
    for question in (
        "First synthetic fixture question?",
        "Second synthetic fixture question?",
        "Third synthetic fixture question?",
    ):
        response = _ask_in_conversation(
            legal_question_client,
            owner_token,
            question=question,
        )
        assert response.status_code == 201
        conversation_ids.append(response.json()["conversation_id"])

    first_page = legal_question_client.get(
        "/api/v1/legal-questions/conversations",
        headers={"Authorization": f"Bearer {owner_token}"},
        params={"limit": 2, "offset": 0},
    )
    second_page = legal_question_client.get(
        "/api/v1/legal-questions/conversations",
        headers={"Authorization": f"Bearer {owner_token}"},
        params={"limit": 2, "offset": 2},
    )
    other_users_page = legal_question_client.get(
        "/api/v1/legal-questions/conversations",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert first_page.status_code == second_page.status_code == 200
    assert first_page.json()["total"] == 3
    assert len(first_page.json()["items"]) == 2
    assert len(second_page.json()["items"]) == 1
    assert len(
        {
            item["id"]
            for item in first_page.json()["items"] + second_page.json()["items"]
        }
    ) == 3
    assert other_users_page.json()["total"] == 0
    assert set(conversation_ids) == {
        item["id"]
        for item in first_page.json()["items"] + second_page.json()["items"]
    }


def test_conversation_access_and_mutations_are_owner_scoped(
    legal_question_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id, owner_token = _login(legal_question_client)
    _, other_token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=owner_id)
    provider = MockQuestionProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )
    created = _ask_in_conversation(
        legal_question_client,
        owner_token,
        question="What does the fixture say?",
    )
    conversation_id = created.json()["conversation_id"]

    read_foreign = legal_question_client.get(
        f"/api/v1/legal-questions/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    continue_foreign = _ask_in_conversation(
        legal_question_client,
        other_token,
        question="Continue another user's conversation",
        conversation_id=conversation_id,
    )
    delete_foreign = legal_question_client.delete(
        f"/api/v1/legal-questions/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    anonymous_read = legal_question_client.get(
        f"/api/v1/legal-questions/conversations/{conversation_id}"
    )

    assert read_foreign.status_code == 404
    assert continue_foreign.status_code == 404
    assert delete_foreign.status_code == 404
    assert anonymous_read.status_code == 401
    assert len(provider.calls) == 1
    assert legal_question_client.get(
        f"/api/v1/legal-questions/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    ).status_code == 200


def test_deleting_conversation_cascades_messages(
    legal_question_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda: MockQuestionProvider(_supported_response(provision)),
    )
    created = _ask_in_conversation(
        legal_question_client,
        token,
        question="Delete this synthetic conversation?",
    )
    conversation_id = UUID(created.json()["conversation_id"])

    deleted = legal_question_client.delete(
        f"/api/v1/legal-questions/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert deleted.status_code == 204
    assert db_session.get(LegalQuestionConversation, conversation_id) is None
    assert (
        db_session.query(LegalQuestionMessage)
        .filter_by(conversation_id=conversation_id)
        .count()
        == 0
    )


def test_conversation_cache_keys_are_isolated_by_user(
    legal_question_client: TestClient,
    answer_cache: MemoryAnswerCache,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_user_id, first_token = _login(legal_question_client)
    second_user_id, second_token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=first_user_id)
    provider = MockQuestionProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )

    first = _ask_in_conversation(
        legal_question_client,
        first_token,
        question="What does the synthetic fixture say?",
    )
    second = _ask_in_conversation(
        legal_question_client,
        second_token,
        question="What does the synthetic fixture say?",
    )

    assert first.status_code == second.status_code == 201
    assert first.json()["answer"]["cache_hit"] is False
    assert second.json()["answer"]["cache_hit"] is False
    assert len(provider.calls) == 2
    assert len(answer_cache.get_calls) == 2
    assert answer_cache.get_calls[0] != answer_cache.get_calls[1]
    assert first_user_id != second_user_id


def test_conversation_context_changes_cache_key(
    legal_question_client: TestClient,
    answer_cache: MemoryAnswerCache,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )
    first = _ask_in_conversation(
        legal_question_client,
        token,
        question="What does the synthetic fixture say?",
    )
    conversation_id = first.json()["conversation_id"]
    continued = _ask_in_conversation(
        legal_question_client,
        token,
        question="What does the synthetic fixture say?",
        conversation_id=conversation_id,
    )

    assert first.status_code == 201
    assert continued.status_code == 200
    assert len(provider.calls) == 2
    assert len(answer_cache.get_calls) == 2
    assert answer_cache.get_calls[0] != answer_cache.get_calls[1]


def test_redis_failure_fails_open_without_cache_hit_or_write(
    legal_question_client: TestClient,
    answer_cache: MemoryAnswerCache,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics_before = legal_question_cache_metrics.snapshot()
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider(_supported_response(provision))
    answer_cache.fail_get = True
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )

    response = _ask(legal_question_client, token)

    assert response.status_code == 200
    assert response.json()["status"] == "answered"
    assert response.json()["cache_hit"] is False
    assert len(provider.calls) == 1
    assert answer_cache.set_calls == []
    metrics_after = legal_question_cache_metrics.snapshot()
    assert metrics_after["errors"] - metrics_before["errors"] == 1


def test_redis_write_failure_still_returns_validated_answer(
    legal_question_client: TestClient,
    answer_cache: MemoryAnswerCache,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider(_supported_response(provision))
    answer_cache.fail_set = True
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )

    response = _ask(legal_question_client, token)

    assert response.status_code == 200
    assert response.json()["status"] == "answered"
    assert response.json()["cache_hit"] is False
    assert len(provider.calls) == 1


def test_ineligible_results_do_not_crowd_out_eligible_evidence(
    legal_question_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    for _ in range(7):
        _add_source(
            db_session,
            user_id=user_id,
            legal_status="unknown",
            text=(
                "What does the synthetic fixture say about wages? "
                "The synthetic fixture says wages may be paid monthly."
            ),
        )
    provision = _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )

    response = _ask(legal_question_client, token)

    assert response.status_code == 200
    assert response.json()["status"] == "answered"
    assert response.json()["citations"][0]["provision_id"] == str(provision.id)
    assert all(
        item["legal_status"] == "current"
        for item in provider.calls[0][1]
    )


def test_source_record_is_rechecked_after_generation(
    legal_question_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)

    class SourceChangingProvider(MockQuestionProvider):
        def answer_legal_question(self, question: str, evidence: list[dict]) -> str:
            provision.legal_source.legal_status = "unknown"
            db_session.commit()
            return super().answer_legal_question(question, evidence)

    provider = SourceChangingProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )

    response = _ask(legal_question_client, token)

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["citations"] == []


@pytest.mark.parametrize(
    "citation_overrides",
    [
        {"source_id": str(uuid4())},
        {"provision_id": str(uuid4())},
        {"article_number": "invented-article"},
        {"sub_article_reference": "invented-subarticle"},
        {"supporting_quote": "An invented provision quote."},
    ],
)
def test_invalid_or_mismatched_citations_are_not_returned_as_answers(
    legal_question_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    citation_overrides: dict,
) -> None:
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider(
        _supported_response(provision, citation=citation_overrides)
    )
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )

    response = _ask(legal_question_client, token)

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["citations"] == []
    assert response.json()["answer"] != provider.response["answer"]


def test_provider_unavailable_returns_clear_service_error(
    legal_question_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    _add_source(db_session, user_id=user_id)

    def unavailable_provider(*args, **kwargs):
        raise LLMProviderError("disabled")

    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        unavailable_provider,
    )
    response = _ask(legal_question_client, token)

    assert response.status_code == 503
    assert "AI answer generation is unavailable" in response.json()["error"]["message"]


def test_provider_rate_limit_returns_clear_retryable_error(
    legal_question_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    _add_source(db_session, user_id=user_id)

    class RateLimitedProvider:
        model_name = "synthetic-question-provider"
        model_version = "fixture-v1"

        def answer_legal_question(self, question: str, evidence: list[dict]) -> str:
            raise LLMProviderRateLimitError("synthetic rate limit")

    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: RateLimitedProvider(),
    )
    response = _ask(legal_question_client, token)

    assert response.status_code == 429
    assert "rate limit was reached" in response.json()["error"]["message"]


def test_invalid_provider_response_returns_clear_upstream_error(
    legal_question_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider({"answer": "Missing required response fields."})
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda *args, **kwargs: provider,
    )

    response = _ask(legal_question_client, token)

    assert response.status_code == 502
    assert "could not produce a valid" in response.json()["error"]["message"]


def test_authentication_and_request_validation(
    legal_question_client: TestClient,
) -> None:
    anonymous = legal_question_client.post(
        "/api/v1/legal-questions/answer",
        json={"question": "Can I ask without logging in?"},
    )
    blank_question = legal_question_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Question Validation User",
            "email": f"{uuid4()}@example.com",
            "password": "a-long-legal-question-test-password",
        },
    )
    assert blank_question.status_code == 201
    login_response = legal_question_client.post(
        "/api/v1/auth/login",
        json={
            "email": blank_question.json()["email"],
            "password": "a-long-legal-question-test-password",
        },
    )
    token = login_response.json()["access_token"]
    blank = _ask(legal_question_client, token, question="   ")
    unverified_context = legal_question_client.post(
        "/api/v1/legal-questions/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question": "Question about an unverified source?",
            "review_context": {"include_unverified": True},
        },
    )

    assert anonymous.status_code == 401
    assert blank.status_code == 422
    assert unverified_context.status_code == 422
