import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Audit,
    Document,
    Feedback,
    Finding,
    FindingCitation,
    LegalProvision,
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


def test_audit_findings_citations_and_feedback_are_related(db_session: Session) -> None:
    user = make_user("Aster", "aster@example.test")
    document = Document(
        owner=user,
        original_filename="employment-contract.pdf",
        storage_key="documents/opaque-key",
        content_type="application/pdf",
        file_size=256,
    )
    audit = Audit(document=document, requester=user)
    source = LegalSource(
        title="Employment source",
        source_type="statute",
        jurisdiction="ET",
        language="en",
    )
    provision = LegalProvision(
        legal_source=source,
        article_number="1",
        text="Provision text",
        language="en",
    )
    finding = Finding(
        audit=audit,
        finding_type="missing_clause",
        severity="medium",
        clause_text="Clause",
        explanation="Explanation",
    )
    citation = FindingCitation(
        finding=finding,
        legal_provision=provision,
        supporting_quote="Relevant text",
    )
    feedback = Feedback(
        finding=finding,
        submitter=user,
        feedback_type="incorrect",
    )
    db_session.add_all([document, source, audit, finding, citation, feedback])
    db_session.commit()

    assert document.audits == [audit]
    assert audit.findings == [finding]
    assert finding.citations == [citation]
    assert citation.legal_provision is provision
    assert finding.feedback == [feedback]
    assert provision.legal_source is source


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


def test_document_file_size_and_finding_confidence_constraints(
    db_session: Session,
) -> None:
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
    db_session.flush()
    audit = Audit(document=valid_document, requester=user)
    db_session.add(audit)
    db_session.flush()
    db_session.add(
        Finding(
            audit=audit,
            finding_type="test",
            severity="low",
            confidence=1.5,
            clause_text="Clause",
            explanation="Explanation",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_audit_history_blocks_document_deletion(db_session: Session) -> None:
    user = make_user("Aster", "aster@example.test")
    document = Document(
        owner=user,
        original_filename="contract.pdf",
        storage_key="documents/key",
        content_type="application/pdf",
        file_size=12,
    )
    audit = Audit(document=document, requester=user)
    db_session.add_all([document, audit])
    db_session.commit()

    db_session.delete(document)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_audit_results_cannot_be_deleted_with_their_audit(
    db_session: Session,
) -> None:
    user = make_user("Aster", "aster@example.test")
    document = Document(
        owner=user,
        original_filename="contract.pdf",
        storage_key="documents/key",
        content_type="application/pdf",
        file_size=12,
    )
    audit = Audit(document=document, requester=user)
    audit.findings.append(
        Finding(
            finding_type="test",
            severity="low",
            clause_text="Clause",
            explanation="Explanation",
        )
    )
    db_session.add(audit)
    db_session.commit()

    db_session.delete(audit)
    with pytest.raises(IntegrityError):
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
