import json
from pathlib import Path
from typing import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.legal_sources import get_legal_source_storage
from app.db.models import LegalProvision, LegalSource, User
from app.db.session import get_db
from app.main import app
from app.storage.interface import LocalPrivateFileStorage

METADATA = {
    "title": "Test Fixture Legal Source",
    "law_number": "TEST-FIXTURE-001",
    "source_type": "statute",
    "jurisdiction": "test-jurisdiction",
    "language": "en",
    "publication_date": "2020-01-01",
    "effective_date": "2020-02-01",
    "version_label": "fixture-v1",
    "original_source_url": "https://example.test/test-fixture.pdf",
}
PROVISIONS = [
    {
        "article_number": "test-article",
        "sub_article_reference": "test-subarticle",
        "section_title": "Test fixture heading",
        "text": "Fixture text for registry tests only.",
        "page_number": 1,
    }
]


@pytest.fixture
def legal_client(
    db_session: Session,
    tmp_path: Path,
) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    storage = LocalPrivateFileStorage(tmp_path / "private-sources")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_legal_source_storage] = lambda: storage
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_legal_source_storage, None)


def _register_and_login(
    client: TestClient,
    db: Session,
    email: str,
    role: str = "user",
) -> tuple[User, str]:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Registry Test User",
            "email": email,
            "password": "a-long-registry-test-password",
        },
    )
    assert registered.status_code == 201
    user = db.get(User, UUID(registered.json()["id"]))
    assert user is not None
    user.role = role
    db.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "a-long-registry-test-password",
        },
    )
    assert login.status_code == 200
    return user, login.json()["access_token"]


def _ingest(
    client: TestClient,
    token: str,
    *,
    version_label: str = "fixture-v1",
    content: bytes = b"%PDF-1.7\nTest fixture PDF\n%%EOF",
):
    metadata = {**METADATA, "version_label": version_label}
    return client.post(
        "/api/v1/legal-sources/ingest",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "metadata_json": json.dumps(metadata),
            "provisions_json": json.dumps(PROVISIONS),
        },
        files={"file": ("test-fixture.pdf", content, "application/pdf")},
    )


def test_source_search_filters_and_paginates(legal_client: TestClient, db_session: Session):
    _, admin_token = _register_and_login(
        legal_client,
        db_session,
        "registry-admin@example.com",
        role="admin",
    )
    first = _ingest(legal_client, admin_token)
    second = _ingest(
        legal_client,
        admin_token,
        version_label="fixture-v2",
        content=b"%PDF-1.7\nDifferent test fixture\n%%EOF",
    )
    assert first.status_code == 201
    assert second.status_code == 201

    by_title = legal_client.get(
        "/api/v1/legal-sources/search",
        params={"title": "Fixture Legal", "limit": 1, "offset": 0},
    )
    by_law_number = legal_client.get(
        "/api/v1/legal-sources",
        params={"law_number": "TEST-FIXTURE", "language": "en"},
    )
    by_article = legal_client.get(
        "/api/v1/legal-sources/search",
        params={"article_number": "test-article", "source_type": "statute"},
    )
    second_page = legal_client.get(
        "/api/v1/legal-sources",
        params={"law_number": "TEST-FIXTURE", "limit": 1, "offset": 1},
    )
    by_status = legal_client.get(
        "/api/v1/legal-sources",
        params={"legal_status": "unknown"},
    )

    assert by_title.status_code == 200
    assert by_title.json()["total"] == 2
    assert len(by_title.json()["items"]) == 1
    assert by_law_number.json()["total"] == 2
    assert by_article.json()["total"] == 2
    assert second_page.json()["total"] == 2
    assert len(second_page.json()["items"]) == 1
    assert by_status.json()["total"] == 2
    assert "source_file_storage_key" not in by_title.json()["items"][0]
    assert all(
        item["legal_status"] == "unknown"
        and item["verification_status"] == "pending"
        and item["eligible_for_findings"] is False
        for item in by_article.json()["items"]
    )


def test_provision_article_and_sub_article_lookup(legal_client: TestClient, db_session: Session):
    _, admin_token = _register_and_login(
        legal_client,
        db_session,
        "article-admin@example.com",
        role="admin",
    )
    ingest = _ingest(legal_client, admin_token)
    source_id = ingest.json()["source"]["id"]

    response = legal_client.get(
        f"/api/v1/legal-sources/{source_id}/provisions",
        params={
            "article_number": "test-article",
            "sub_article_reference": "test-subarticle",
            "language": "en",
        },
    )

    assert response.status_code == 200
    provision = response.json()["items"][0]
    assert response.json()["total"] == 1
    assert provision["article_number"] == "test-article"
    assert provision["sub_article_reference"] == "test-subarticle"
    assert provision["page_number"] == 1


def test_duplicate_file_is_rejected_without_overwriting_existing_version(
    legal_client: TestClient,
    db_session: Session,
    tmp_path: Path,
):
    _, admin_token = _register_and_login(
        legal_client,
        db_session,
        "duplicate-admin@example.com",
        role="admin",
    )
    first = _ingest(legal_client, admin_token)
    duplicate = _ingest(
        legal_client,
        admin_token,
        version_label="fixture-v2",
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert db_session.scalar(select(func.count(LegalSource.id))) == 1
    stored_files = list((tmp_path / "private-sources").rglob("*.pdf"))
    assert len(stored_files) == 1


def test_changed_source_is_preserved_as_a_distinct_version(
    legal_client: TestClient,
    db_session: Session,
):
    _, admin_token = _register_and_login(
        legal_client,
        db_session,
        "versions-admin@example.com",
        role="admin",
    )
    old_version = _ingest(legal_client, admin_token)
    new_version = _ingest(
        legal_client,
        admin_token,
        version_label="fixture-v2",
        content=b"%PDF-1.7\nChanged fixture document\n%%EOF",
    )

    assert old_version.status_code == new_version.status_code == 201
    records = db_session.scalars(
        select(LegalSource).order_by(LegalSource.version_label)
    ).all()
    assert [record.version_label for record in records] == [
        "fixture-v1",
        "fixture-v2",
    ]
    assert records[0].file_checksum != records[1].file_checksum
    assert db_session.scalar(select(func.count(LegalProvision.id))) == 2


def test_only_admin_can_ingest_or_verify_and_verification_requires_second_reviewer(
    legal_client: TestClient,
    db_session: Session,
):
    ingester, ingester_token = _register_and_login(
        legal_client,
        db_session,
        "ingester@example.com",
        role="admin",
    )
    _, reviewer_token = _register_and_login(
        legal_client,
        db_session,
        "reviewer@example.com",
        role="admin",
    )
    _, user_token = _register_and_login(
        legal_client,
        db_session,
        "ordinary@example.com",
    )

    denied = _ingest(legal_client, user_token)
    ingested = _ingest(legal_client, ingester_token)
    source_id = ingested.json()["source"]["id"]
    self_review = legal_client.post(
        f"/api/v1/legal-sources/{source_id}/verify",
        headers={"Authorization": f"Bearer {ingester_token}"},
        json={
            "decision": "verified",
            "legal_status": "current",
            "verification_notes": "Reviewed against test fixture only.",
        },
    )
    denied_review = legal_client.post(
        f"/api/v1/legal-sources/{source_id}/verify",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "decision": "verified",
            "legal_status": "current",
            "verification_notes": "Reviewed against test fixture only.",
        },
    )
    approved = legal_client.post(
        f"/api/v1/legal-sources/{source_id}/verify",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={
            "decision": "verified",
            "legal_status": "current",
            "verification_notes": "Reviewed against test fixture only.",
        },
    )

    assert denied.status_code == 403
    assert ingested.status_code == 201
    assert ingester.id != db_session.get(
        LegalSource, UUID(source_id)
    ).verified_by
    assert self_review.status_code == 403
    assert denied_review.status_code == 403
    assert approved.status_code == 200
    assert approved.json()["eligible_for_findings"] is True
    assert approved.json()["verified_by"] is not None


def test_unknown_status_stays_ineligible_even_after_source_verification(
    legal_client: TestClient,
    db_session: Session,
):
    _, ingester_token = _register_and_login(
        legal_client,
        db_session,
        "unknown-ingester@example.com",
        role="admin",
    )
    _, reviewer_token = _register_and_login(
        legal_client,
        db_session,
        "unknown-reviewer@example.com",
        role="admin",
    )
    ingested = _ingest(legal_client, ingester_token)
    source_id = ingested.json()["source"]["id"]

    response = legal_client.post(
        f"/api/v1/legal-sources/{source_id}/verify",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={
            "decision": "verified",
            "legal_status": "unknown",
            "verification_notes": "Applicability evidence is insufficient.",
        },
    )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "verified"
    assert response.json()["legal_status"] == "unknown"
    assert response.json()["eligible_for_findings"] is False


def test_rejected_source_is_not_publicly_searchable(
    legal_client: TestClient,
    db_session: Session,
):
    _, ingester_token = _register_and_login(
        legal_client,
        db_session,
        "reject-ingester@example.com",
        role="admin",
    )
    _, reviewer_token = _register_and_login(
        legal_client,
        db_session,
        "reject-reviewer@example.com",
        role="admin",
    )
    ingested = _ingest(legal_client, ingester_token)
    source_id = ingested.json()["source"]["id"]

    response = legal_client.post(
        f"/api/v1/legal-sources/{source_id}/verify",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={
            "decision": "rejected",
            "legal_status": "unknown",
            "verification_notes": "The provenance could not be confirmed.",
        },
    )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "rejected"
    assert legal_client.get(f"/api/v1/legal-sources/{source_id}").status_code == 404
    assert legal_client.get("/api/v1/legal-sources").json()["total"] == 0
