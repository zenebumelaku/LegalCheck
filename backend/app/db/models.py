import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("length(name) > 0", name="ck_users_name_nonempty"),
        CheckConstraint("length(email) > 0", name="ck_users_email_nonempty"),
        CheckConstraint("length(role) > 0", name="ck_users_role_nonempty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="owner",
        passive_deletes="all",
    )
    requested_audits: Mapped[List["Audit"]] = relationship(
        back_populates="requester",
        passive_deletes="all",
    )
    submitted_feedback: Mapped[List["Feedback"]] = relationship(
        back_populates="submitter",
        passive_deletes="all",
    )


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (CheckConstraint("length(name) > 0", name="ck_organizations_name_nonempty"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    organization_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="organization",
        passive_deletes=True,
    )


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
        CheckConstraint(
            "length(membership_role) > 0",
            name="ck_membership_role_nonempty",
        ),
        Index("ix_memberships_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    membership_role: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")


class LegalSource(Base):
    __tablename__ = "legal_sources"
    __table_args__ = (
        UniqueConstraint(
            "law_number",
            "version_label",
            name="uq_legal_source_law_version",
        ),
        CheckConstraint(
            "legal_status IN ('unknown', 'active', 'amended', 'repealed', 'superseded')",
            name="ck_legal_sources_status",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'pending', 'verified', 'rejected')",
            name="ck_legal_sources_verification_status",
        ),
        CheckConstraint(
            "end_date IS NULL OR effective_date IS NULL OR end_date >= effective_date",
            name="ck_legal_sources_dates",
        ),
        Index("ix_legal_sources_jurisdiction_type", "jurisdiction", "source_type"),
        Index("ix_legal_sources_effective_date", "effective_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    law_number: Mapped[Optional[str]] = mapped_column(String(100))
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    publication_date: Mapped[Optional[date]] = mapped_column(Date)
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    legal_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    version_label: Mapped[Optional[str]] = mapped_column(String(100))
    original_source_url: Mapped[Optional[str]] = mapped_column(String(2048))
    file_checksum: Mapped[Optional[str]] = mapped_column(String(128))
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="unverified"
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    provisions: Mapped[List["LegalProvision"]] = relationship(
        back_populates="legal_source",
        passive_deletes="all",
    )


class LegalProvision(Base):
    __tablename__ = "legal_provisions"
    __table_args__ = (
        UniqueConstraint(
            "legal_source_id",
            "article_number",
            "section_title",
            name="uq_legal_provision_source_article_section",
        ),
        CheckConstraint("page_number IS NULL OR page_number > 0", name="ck_provisions_page_number"),
        Index("ix_legal_provisions_article_number", "article_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    legal_source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legal_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    article_number: Mapped[str] = mapped_column(String(100), nullable=False)
    section_title: Mapped[Optional[str]] = mapped_column(String(500))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )

    legal_source: Mapped["LegalSource"] = relationship(back_populates="provisions")
    citations: Mapped[List["FindingCitation"]] = relationship(
        back_populates="legal_provision",
        passive_deletes="all",
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("file_size >= 0", name="ck_documents_file_size"),
        Index("ix_documents_owner_created", "owner_user_id", "created_at"),
        Index("ix_documents_organization_id", "organization_id"),
        Index("ix_documents_status", "processing_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[Optional[str]] = mapped_column(String(128))
    detected_language: Mapped[Optional[str]] = mapped_column(String(50))
    document_type: Mapped[Optional[str]] = mapped_column(String(100))
    processing_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    owner: Mapped["User"] = relationship(back_populates="documents")
    organization: Mapped[Optional["Organization"]] = relationship(back_populates="documents")
    audits: Mapped[List["Audit"]] = relationship(
        back_populates="document",
        passive_deletes="all",
    )


class Audit(Base):
    __tablename__ = "audits"
    __table_args__ = (
        CheckConstraint(
            "audit_status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_audits_status",
        ),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name="ck_audits_completion_time",
        ),
        Index("ix_audits_document_created", "document_id", "created_at"),
        Index("ix_audits_requester_created", "requested_by", "created_at"),
        Index("ix_audits_status", "audit_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    audit_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    review_options: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    analysis_version: Mapped[Optional[str]] = mapped_column(String(100))
    model_identifier: Mapped[Optional[str]] = mapped_column(String(255))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[Optional[str]] = mapped_column(String(100))
    failure_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="audits")
    requester: Mapped["User"] = relationship(back_populates="requested_audits")
    findings: Mapped[List["Finding"]] = relationship(
        back_populates="audit",
        passive_deletes="all",
    )


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('informational', 'low', 'medium', 'high', 'critical')",
            name="ck_findings_severity",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_findings_confidence",
        ),
        Index("ix_findings_audit_severity", "audit_id", "severity"),
        Index("ix_findings_type", "finding_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("audits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[Optional[str]] = mapped_column(Text)
    evidence_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="unverified"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    audit: Mapped["Audit"] = relationship(back_populates="findings")
    citations: Mapped[List["FindingCitation"]] = relationship(
        back_populates="finding",
        passive_deletes="all",
    )
    feedback: Mapped[List["Feedback"]] = relationship(
        back_populates="finding",
        passive_deletes="all",
    )


class FindingCitation(Base):
    __tablename__ = "finding_citations"
    __table_args__ = (
        UniqueConstraint(
            "finding_id",
            "legal_provision_id",
            name="uq_finding_citation_provision",
        ),
        Index("ix_finding_citations_legal_provision_id", "legal_provision_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("findings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    legal_provision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legal_provisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    supporting_quote: Mapped[Optional[str]] = mapped_column(Text)
    relevance_information: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    finding: Mapped["Finding"] = relationship(back_populates="citations")
    legal_provision: Mapped["LegalProvision"] = relationship(back_populates="citations")


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (Index("ix_feedback_finding_created", "finding_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("findings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    feedback_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    finding: Mapped["Finding"] = relationship(back_populates="feedback")
    submitter: Mapped["User"] = relationship(back_populates="submitted_feedback")
