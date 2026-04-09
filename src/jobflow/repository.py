from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobflow.db import ApplicationLedgerEntry, Job, JobSourceRecord, utc_now
from jobflow.domain import ApplyPreview, CanonicalJob, ReviewStatus


@dataclass
class UpsertOutcome:
    job_id: str
    created: bool
    updated: bool
    deduped: bool


def canonical_fingerprint(job: CanonicalJob) -> str:
    parts = [
        _normalize(job.company),
        _normalize(job.title),
        _normalize(job.location_text),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def source_board_ref(job: CanonicalJob) -> str | None:
    return str(job.metadata.get("board_ref")) if job.metadata.get("board_ref") else None


class JobRepository:
    def __init__(self, engine) -> None:
        self.engine = engine

    def upsert_job(
        self, job_input: CanonicalJob, *, score: float, reasons: list[str]
    ) -> UpsertOutcome:
        fingerprint = canonical_fingerprint(job_input)
        now = utc_now()

        with Session(self.engine) as session:
            source_record = session.execute(
                select(JobSourceRecord).where(
                    JobSourceRecord.source_name == job_input.source_name,
                    JobSourceRecord.external_id == job_input.external_id,
                )
            ).scalar_one_or_none()

            created = False
            updated = False
            deduped = False

            if source_record is not None:
                job = session.get(Job, source_record.job_id)
                if job is None:
                    raise RuntimeError("Source record points to missing job")
                updated = True
            else:
                job = session.execute(
                    select(Job).where(Job.fingerprint == fingerprint)
                ).scalar_one_or_none()
                if job is None:
                    job = Job(
                        fingerprint=fingerprint,
                        primary_source_family=job_input.family.value,
                        company=job_input.company,
                        title=job_input.title,
                        location_text=job_input.location_text,
                        location_country=job_input.location_country,
                        location_region=job_input.location_region,
                        workplace_type=job_input.workplace_type.value,
                        employment_type=job_input.employment_type,
                        description=job_input.description,
                        job_url=job_input.job_url,
                        apply_url=job_input.apply_url,
                        score=score,
                        score_reasons=reasons,
                        first_seen_at=now,
                        last_seen_at=now,
                        updated_at=now,
                    )
                    session.add(job)
                    session.flush()
                    created = True
                else:
                    deduped = True
                    updated = True

                source_record = JobSourceRecord(
                    job_id=job.id,
                    source_name=job_input.source_name,
                    family=job_input.family.value,
                    external_id=job_input.external_id,
                    board_ref=source_board_ref(job_input),
                    job_url=job_input.job_url,
                    apply_url=job_input.apply_url,
                    raw_payload=job_input.raw_payload,
                    source_metadata=job_input.metadata,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(source_record)

            job.fingerprint = fingerprint
            job.primary_source_family = job_input.family.value
            job.company = _prefer_required(job_input.company, job.company)
            job.title = _prefer_required(job_input.title, job.title)
            job.location_text = _prefer_required(
                job_input.location_text, job.location_text
            )
            job.location_country = _prefer(
                job_input.location_country, job.location_country
            )
            job.location_region = _prefer(
                job_input.location_region, job.location_region
            )
            job.workplace_type = job_input.workplace_type.value
            job.employment_type = _prefer(
                job_input.employment_type, job.employment_type
            )
            job.description = _prefer(job_input.description, job.description)
            job.job_url = _prefer_required(job_input.job_url, job.job_url)
            job.apply_url = _prefer(job_input.apply_url, job.apply_url)
            job.score = score
            job.score_reasons = reasons
            job.last_seen_at = now
            job.updated_at = now

            source_record.job_url = job_input.job_url
            source_record.apply_url = job_input.apply_url
            source_record.raw_payload = job_input.raw_payload
            source_record.source_metadata = job_input.metadata
            source_record.board_ref = source_board_ref(job_input)
            source_record.last_seen_at = now

            source_count = (
                session.execute(
                    select(JobSourceRecord).where(JobSourceRecord.job_id == job.id)
                )
                .scalars()
                .all()
            )
            job.source_count = len(source_count)

            session.add(job)
            session.add(source_record)
            session.commit()
            return UpsertOutcome(
                job_id=job.id, created=created, updated=updated, deduped=deduped
            )

    def list_jobs(
        self,
        *,
        limit: int = 20,
        review_status: ReviewStatus | None = None,
        family: str | None = None,
    ) -> list[Job]:
        with Session(self.engine) as session:
            query = select(Job)
            if review_status is not None:
                query = query.where(Job.review_status == review_status.value)
            if family is not None:
                query = query.where(Job.primary_source_family == family)
            jobs = list(session.execute(query).scalars().all())
            jobs.sort(key=lambda item: (item.score, item.last_seen_at), reverse=True)
            return jobs[:limit]

    def get_job(self, job_id: str) -> Job | None:
        with Session(self.engine) as session:
            return session.get(Job, job_id)

    def get_sources_for_job(self, job_id: str) -> list[JobSourceRecord]:
        with Session(self.engine) as session:
            return list(
                session.execute(
                    select(JobSourceRecord).where(JobSourceRecord.job_id == job_id)
                )
                .scalars()
                .all()
            )

    def update_review(
        self, job_id: str, decision: ReviewStatus, notes: str | None = None
    ) -> Job:
        with Session(self.engine) as session:
            job = session.get(Job, job_id)
            if job is None:
                raise KeyError(f"Job not found: {job_id}")
            job.review_status = decision.value
            if notes:
                job.review_notes = notes
            job.updated_at = utc_now()
            session.add(job)
            session.commit()
            session.refresh(job)
            return job

    def record_application(self, preview: ApplyPreview) -> ApplicationLedgerEntry:
        with Session(self.engine) as session:
            entry = ApplicationLedgerEntry(
                job_id=preview.job_id,
                source_name=preview.source_name,
                source_family=preview.family.value,
                requested_mode="dry_run" if preview.dry_run else "live",
                dry_run=preview.dry_run,
                status=preview.status,
                endpoint=preview.endpoint,
                payload_preview=preview.payload_preview,
                response_preview=preview.response_preview,
                note=preview.note,
                created_at=preview.created_at,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry

    def application_entries(self) -> list[ApplicationLedgerEntry]:
        with Session(self.engine) as session:
            return list(session.execute(select(ApplicationLedgerEntry)).scalars().all())

    def counts(self) -> tuple[int, int, int]:
        with Session(self.engine) as session:
            return (
                len(session.execute(select(Job)).scalars().all()),
                len(session.execute(select(JobSourceRecord)).scalars().all()),
                len(session.execute(select(ApplicationLedgerEntry)).scalars().all()),
            )


def _normalize(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", value.strip().lower())
    return collapsed


def _prefer(candidate: str | None, existing: str | None) -> str | None:
    return candidate or existing


def _prefer_required(candidate: str, existing: str) -> str:
    return candidate or existing
