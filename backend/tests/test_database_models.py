import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    LegalSource,
    Organization,
    OrganizationMembership,
    User,
)


def make_user(name: str, email: str) -> User:
    return User(name=name, email=email, password_hash="test-hash")


def test_user_organization_membership_relationships(db_session: Session) -> None:
    user = make_user("Aster", "aster@example.test")
    organization = Organization(name="Example Org", organization_type="employer")
    membership = OrganizationMembership(
        organization=organization,
        user=user,
        membership_role="admin",
    )
    db_session.add(membership)
    db_session.commit()

    assert user.memberships == [membership]
    assert organization.memberships == [membership]
    assert membership.user is user
    assert membership.organization is organization
    assert isinstance(user.id, uuid.UUID)
    assert isinstance(organization.id, uuid.UUID)


def test_unique_user_email_and_membership_constraint(db_session: Session) -> None:
    user = make_user("Aster", "aster@example.test")
    organization = Organization(name="Example Org", organization_type="employer")
    db_session.add_all([user, organization])
    db_session.flush()
    db_session.add(
        OrganizationMembership(
            organization=organization,
            user=user,
            membership_role="admin",
        )
    )
    db_session.commit()

    db_session.add(make_user("Another", "aster@example.test"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(make_user("Case Variant", " Aster@example.test "))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(
        OrganizationMembership(
            organization_id=organization.id,
            user_id=user.id,
            membership_role="member",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_document_file_size_constraint(db_session: Session) -> None:
    user = make_user("Aster", "aster@example.test")
    db_session.add(user)
    db_session.commit()
    document = Document(
        owner=user,
        original_filename="contract.pdf",
        storage_key="documents/key",
        content_type="application/pdf",
        file_size=-1,
    )
    db_session.add(document)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    valid_document = Document(
        owner=user,
        original_filename="contract.pdf",
        storage_key="documents/key",
        content_type="application/pdf",
        file_size=0,
    )
    db_session.add(valid_document)
    db_session.commit()


def test_legal_source_versions_are_distinct_and_not_current_by_default(
    db_session: Session,
) -> None:
    source_v1 = LegalSource(
        title="Employment source",
        law_number="EXAMPLE",
        version_label="1",
        source_type="statute",
        jurisdiction="ET",
        language="en",
    )
    source_v2 = LegalSource(
        title="Employment source",
        law_number="EXAMPLE",
        version_label="2",
        source_type="statute",
        jurisdiction="ET",
        language="en",
    )
    db_session.add_all([source_v1, source_v2])
    db_session.commit()

    assert source_v1.id != source_v2.id
    assert source_v1.legal_status == "unknown"
    assert source_v1.verification_status == "unverified"
