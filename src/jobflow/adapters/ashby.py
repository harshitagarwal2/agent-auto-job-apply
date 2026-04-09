from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from jobflow.adapters.base import (
    BaseDiscoveryAdapter,
    as_string,
    detect_workplace_type,
    infer_country,
)
from jobflow.domain import CanonicalJob, SourceConfig


class AshbyAdapter(BaseDiscoveryAdapter):
    def discover(
        self,
        source: SourceConfig,
        *,
        base_dir: Path,
        timeout_seconds: float,
    ) -> list[CanonicalJob]:
        payload = self.load_payload(
            source, base_dir=base_dir, timeout_seconds=timeout_seconds
        )
        items = _extract_items(payload)
        jobs: list[CanonicalJob] = []
        for item in items:
            location_text = _extract_location(item)
            job_url = as_string(
                item.get("jobUrl") or item.get("applyUrl") or item.get("url"),
                default="",
            )
            jobs.append(
                CanonicalJob(
                    source_name=source.name,
                    family=source.family,
                    external_id=as_string(
                        item.get("id") or item.get("jobId") or item.get("_id")
                    ),
                    company=source.company_fallback(),
                    title=as_string(
                        item.get("title") or item.get("name") or item.get("jobTitle")
                    ),
                    location_text=location_text,
                    location_country=infer_country(location_text),
                    employment_type=as_string(item.get("employmentType")) or None,
                    description=item.get("descriptionPlain")
                    or item.get("descriptionHtml")
                    or item.get("description"),
                    workplace_type=detect_workplace_type(location_text),
                    job_url=job_url,
                    apply_url=as_string(item.get("applyUrl")) or job_url,
                    posted_at=_parse_datetime(
                        item.get("publishedAt") or item.get("updatedAt")
                    ),
                    raw_payload=item,
                )
            )
        return jobs


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    for key in ("jobs", "jobPosts", "openings", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    job_board = payload.get("jobBoard", {})
    if isinstance(job_board.get("jobPostings"), list):
        return job_board["jobPostings"]
    return []


def _extract_location(item: dict[str, Any]) -> str:
    location = item.get("location")
    if isinstance(location, dict):
        return as_string(location.get("name"), default="United States")
    if isinstance(location, list):
        return ", ".join(
            as_string(entry.get("name") if isinstance(entry, dict) else entry)
            for entry in location
        )
    return as_string(
        item.get("locationName") or item.get("jobLocation"), default="United States"
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
