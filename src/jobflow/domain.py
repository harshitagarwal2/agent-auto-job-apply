from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


DEFAULT_ROLE_KEYWORDS = [
    "software engineer",
    "product manager",
    "program manager",
    "business analyst",
]


class SourceFamily(str, Enum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKDAY = "workday"
    LINKEDIN = "linkedin"
    GLASSDOOR = "glassdoor"


class ApplyMode(str, Enum):
    DISABLED = "disabled"
    DRY_RUN_ONLY = "dry_run_only"
    LIVE_OPT_IN = "live_opt_in"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    APPLIED = "applied"


class WorkplaceType(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ON_SITE = "on_site"
    UNSPECIFIED = "unspecified"


class DatabaseConfig(BaseModel):
    path: Path = Path(".local/jobflow.sqlite3")


class ApplyConfig(BaseModel):
    allow_live_submit: bool = False
    default_source_tag: str = "jobflow-local"


class SearchProfile(BaseModel):
    role_keywords: list[str] = Field(
        default_factory=lambda: DEFAULT_ROLE_KEYWORDS.copy()
    )
    allowed_countries: list[str] = Field(
        default_factory=lambda: ["US", "USA", "United States"]
    )
    preferred_locations: list[str] = Field(
        default_factory=lambda: ["Remote", "United States", "USA"]
    )
    exclude_keywords: list[str] = Field(default_factory=list)


class SourcePolicy(BaseModel):
    discovery_enabled: bool = True
    apply_mode: ApplyMode | None = None
    allow_live_apply: bool = False


class ManualLead(BaseModel):
    external_id: str
    title: str
    company: str
    location_text: str = "United States"
    location_country: str | None = "US"
    description: str | None = None
    job_url: str
    apply_url: str | None = None
    posted_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceConfig(BaseModel):
    name: str
    family: SourceFamily
    enabled: bool = True
    company: str | None = None
    board_token: str | None = None
    site: str | None = None
    region: str = "global"
    jobs_url: str | None = None
    feed_path: Path | None = None
    api_key_env: str | None = None
    manual_leads: list[ManualLead] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    policy: SourcePolicy = Field(default_factory=SourcePolicy)

    def resolved_feed_path(self, base_dir: Path) -> Path | None:
        if self.feed_path is None:
            return None
        if self.feed_path.is_absolute():
            return self.feed_path
        return base_dir / self.feed_path

    def company_fallback(self) -> str:
        return self.company or self.name


class AppConfig(BaseModel):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    profile: SearchProfile = Field(default_factory=SearchProfile)
    apply: ApplyConfig = Field(default_factory=ApplyConfig)
    sources: list[SourceConfig] = Field(default_factory=list)
    request_timeout_seconds: float = 20.0

    def resolved_database_path(self, base_dir: Path) -> Path:
        db_path = self.database.path
        if db_path.is_absolute():
            return db_path
        return base_dir / db_path


class CanonicalJob(BaseModel):
    source_name: str
    family: SourceFamily
    external_id: str
    company: str
    title: str
    location_text: str
    location_country: str | None = None
    location_region: str | None = None
    workplace_type: WorkplaceType = WorkplaceType.UNSPECIFIED
    employment_type: str | None = None
    description: str | None = None
    job_url: str
    apply_url: str | None = None
    posted_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class ApplicantProfile(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    current_company: str | None = None
    resume_path: Path | None = None
    cover_letter_path: Path | None = None
    links: dict[str, str] = Field(default_factory=dict)
    comments: str | None = None


class RankedJob(BaseModel):
    score: float
    reasons: list[str]


class SyncStats(BaseModel):
    sources_seen: int = 0
    jobs_seen: int = 0
    created: int = 0
    updated: int = 0
    deduped: int = 0
    blocked: int = 0
    errors: list[str] = Field(default_factory=list)


class ApplyPreview(BaseModel):
    status: str
    job_id: str
    source_name: str
    family: SourceFamily
    dry_run: bool
    endpoint: str | None = None
    payload_preview: dict[str, Any] = Field(default_factory=dict)
    response_preview: dict[str, Any] = Field(default_factory=dict)
    note: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResolvedSourcePolicy(BaseModel):
    discovery_enabled: bool
    dry_run_apply_allowed: bool
    live_apply_allowed: bool
    apply_capable_family: bool
    effective_apply_mode: ApplyMode
