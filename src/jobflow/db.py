from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "job"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    fingerprint: Mapped[str] = mapped_column(String, unique=True, index=True)
    primary_source_family: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    location_text: Mapped[str] = mapped_column(String)
    location_country: Mapped[str | None] = mapped_column(String, nullable=True)
    location_region: Mapped[str | None] = mapped_column(String, nullable=True)
    workplace_type: Mapped[str] = mapped_column(String, default="unspecified")
    employment_type: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_url: Mapped[str] = mapped_column(String)
    apply_url: Mapped[str | None] = mapped_column(String, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    score_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    review_status: Mapped[str] = mapped_column(String, default="pending", index=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_count: Mapped[int] = mapped_column(Integer, default=1)

    sources: Mapped[list["JobSourceRecord"]] = relationship(back_populates="job")
    applications: Mapped[list["ApplicationLedgerEntry"]] = relationship(
        back_populates="job"
    )


class JobSourceRecord(Base):
    __tablename__ = "job_source_record"
    __table_args__ = (
        UniqueConstraint(
            "source_name", "external_id", name="uq_source_name_external_id"
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    job_id: Mapped[str] = mapped_column(ForeignKey("job.id"), index=True)
    source_name: Mapped[str] = mapped_column(String, index=True)
    family: Mapped[str] = mapped_column(String, index=True)
    external_id: Mapped[str] = mapped_column(String)
    board_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    job_url: Mapped[str] = mapped_column(String)
    apply_url: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    job: Mapped[Job] = relationship(back_populates="sources")


class ApplicationLedgerEntry(Base):
    __tablename__ = "application_ledger_entry"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    job_id: Mapped[str] = mapped_column(ForeignKey("job.id"), index=True)
    source_name: Mapped[str] = mapped_column(String)
    source_family: Mapped[str] = mapped_column(String, index=True)
    requested_mode: Mapped[str] = mapped_column(String)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String, index=True)
    endpoint: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_preview: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    response_preview: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )

    job: Mapped[Job] = relationship(back_populates="applications")


def make_engine(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def session_for(engine) -> Session:
    return Session(engine)
