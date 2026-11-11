import uuid
from datetime import date, datetime
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
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text as sql_text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class EmbeddingVector(TypeDecorator[list[float]]):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(384))
        return dialect.type_descriptor(JSON())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index(
            "uq_users_email_normalized",
            sql_text("lower(trim(email))"),
            unique=True,
        ),
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
    auth_sessions: Mapped[List["AuthSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    password_reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    legal_question_conversations: Mapped[List["LegalQuestionConversation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_user_expiry", "user_id", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="auth_sessions")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index(
            "ix_password_reset_tokens_user_expiry",
            "user_id",
            "expires_at",
        ),
        Index("ix_password_reset_tokens_expiry", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="password_reset_tokens")


class LegalQuestionConversation(Base):
    __tablename__ = "legal_question_conversations"
    __table_args__ = (
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_legal_question_conversations_title_nonempty",
        ),
        Index(
            "ix_legal_question_conversations_user_updated",
            "user_id",
            "updated_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="legal_question_conversations")
    messages: Mapped[List["LegalQuestionMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="LegalQuestionMessage.turn_index, LegalQuestionMessage.role",
    )


class LegalQuestionMessage(Base):
    __tablename__ = "legal_question_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_legal_question_messages_role",
        ),
        CheckConstraint(
            "turn_index >= 0",
            name="ck_legal_question_messages_turn_index",
        ),
        CheckConstraint(
            "length(content) > 0",
            name="ck_legal_question_messages_content_nonempty",
        ),
        UniqueConstraint(
            "conversation_id",
            "turn_index",
            "role",
            name="uq_legal_question_message_turn_role",
        ),
        Index(
            "ix_legal_question_messages_conversation_turn",
            "conversation_id",
            "turn_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legal_question_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    answer_status: Mapped[Optional[str]] = mapped_column(String(30))
    review_date: Mapped[Optional[date]] = mapped_column(Date)
    citations_snapshot: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    model_name: Mapped[Optional[str]] = mapped_column(String(255))
    model_version: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    conversation: Mapped["LegalQuestionConversation"] = relationship(
        back_populates="messages"
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
            "legal_status IN ('unknown', 'current', 'active', 'amended', 'repealed', 'superseded')",
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
        UniqueConstraint(
            "source_file_storage_key",
            name="uq_legal_sources_storage_key",
        ),
        Index("ix_legal_sources_jurisdiction_type", "jurisdiction", "source_type"),
        Index("ix_legal_sources_effective_date", "effective_date"),
        Index("uq_legal_sources_file_checksum", "file_checksum", unique=True),
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
    source_file_storage_key: Mapped[Optional[str]] = mapped_column(String(1024))
    ingested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_legal_sources_ingested_by_users",
        ),
    )
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_legal_sources_verified_by_users",
        ),
    )
    verification_notes: Mapped[Optional[str]] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="unverified"
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    applicability_reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_legal_sources_applicability_reviewed_by_users",
        ),
    )
    applicability_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    applicability_review_notes: Mapped[Optional[str]] = mapped_column(Text)
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
    applicability_reviews: Mapped[List["LegalSourceApplicabilityReview"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def eligible_for_findings(self) -> bool:
        return (
            self.verification_status == "verified"
            and self.legal_status == "current"
            and self.effective_date is not None
            and self.file_checksum is not None
            and self.source_file_storage_key is not None
            and self.verified_by is not None
            and self.verified_at is not None
            and (self.original_source_url is not None or self.source_type == "uploaded_document")
        )


class LegalSourceApplicabilityReview(Base):
    __tablename__ = "legal_source_applicability_reviews"
    __table_args__ = (
        Index(
            "ix_legal_source_applicability_reviews_source_time",
            "source_id",
            "reviewed_at",
        ),
        CheckConstraint(
            "legal_status IN ('unknown', 'current', 'amended', 'repealed', 'superseded')",
            name="ck_legal_source_applicability_reviews_status",
        ),
        CheckConstraint(
            "end_date IS NULL OR effective_date IS NULL OR end_date >= effective_date",
            name="ck_legal_source_applicability_reviews_dates",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legal_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    legal_status: Mapped[str] = mapped_column(String(30), nullable=False)
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    verification_notes: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    source: Mapped["LegalSource"] = relationship(
        back_populates="applicability_reviews"
    )


class LegalProvision(Base):
    __tablename__ = "legal_provisions"
    __table_args__ = (
        UniqueConstraint(
            "legal_source_id",
            "article_number",
            "sub_article_reference",
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
    sub_article_reference: Mapped[Optional[str]] = mapped_column(String(100))
    section_title: Mapped[Optional[str]] = mapped_column(String(500))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )

    legal_source: Mapped["LegalSource"] = relationship(back_populates="provisions")


Index(
    "ix_legal_provisions_text_search",
    func.to_tsvector("simple", LegalProvision.text),
    postgresql_using="gin",
).ddl_if(dialect="postgresql")


class LegalProvisionChunk(Base):
    __tablename__ = "legal_provision_chunks"
    __table_args__ = (
        UniqueConstraint(
            "provision_id",
            "chunk_index",
            "embedding_model",
            "embedding_version",
            name="uq_provision_chunk_model_version",
        ),
        CheckConstraint("chunk_index >= 0", name="ck_provision_chunks_index"),
        CheckConstraint("length(chunk_text) > 0", name="ck_provision_chunks_text"),
        CheckConstraint(
            "length(embedding_model) > 0",
            name="ck_provision_chunks_embedding_model",
        ),
        CheckConstraint(
            "length(embedding_version) > 0",
            name="ck_provision_chunks_embedding_version",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_provision_chunks_page_number",
        ),
        Index("ix_provision_chunks_provision_id", "provision_id"),
        Index(
            "ix_provision_chunks_embedding_model_version",
            "embedding_model",
            "embedding_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legal_provisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    source_version_label: Mapped[Optional[str]] = mapped_column(String(100))
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(EmbeddingVector())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    provision: Mapped["LegalProvision"] = relationship()


Index(
    "ix_provision_chunks_embedding_search",
    LegalProvisionChunk.embedding,
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_cosine_ops"},
    postgresql_where=LegalProvisionChunk.embedding.is_not(None),
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
