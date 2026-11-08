import json
from datetime import date, datetime, timezone
from typing import Generator, Optional
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import LegalProvision, LegalSource
from app.db.session import get_db
from app.main import app
from app.services.llm_provider import LLMProviderError


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
def legal_question_client(
    db_session: Session,
) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
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

    def unavailable_provider():
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


def test_eligible_retrieved_evidence_is_answered_and_cited(
    legal_question_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, token = _login(legal_question_client)
    provision = _add_source(db_session, user_id=user_id)
    provider = MockQuestionProvider(_supported_response(provision))
    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        lambda: provider,
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
    assert provider.calls[0][1][0]["provision_id"] == str(provision.id)


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
        lambda: provider,
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
        lambda: provider,
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
        lambda: provider,
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

    def unavailable_provider():
        raise LLMProviderError("disabled")

    monkeypatch.setattr(
        "app.services.legal_question_answering.get_llm_provider",
        unavailable_provider,
    )
    response = _ask(legal_question_client, token)

    assert response.status_code == 503
    assert "AI answer generation is unavailable" in response.json()["error"]["message"]


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
        lambda: provider,
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
