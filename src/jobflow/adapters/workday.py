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


class WorkdayAdapter(BaseDiscoveryAdapter):
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
            location_text = as_string(
                item.get("locationsText")
                or item.get("location")
                or item.get("primaryLocation")
                or item.get("locations"),
                default="United States",
            )
            external_path = as_string(
                item.get("externalPath") or item.get("jobUrl"), default=""
            )
            if external_path and source.jobs_url and external_path.startswith("/"):
                base = source.jobs_url.rstrip("/")
                external_path = f"{base}{external_path}"

            jobs.append(
                CanonicalJob(
                    source_name=source.name,
                    family=source.family,
                    external_id=as_string(
                        item.get("bulletFields", [None])[0]
                        or item.get("id")
                        or item.get("jobId")
                    ),
                    company=source.company_fallback(),
                    title=as_string(
                        item.get("title") or item.get("jobTitle") or item.get("name")
                    ),
                    location_text=location_text,
                    location_country=infer_country(location_text),
                    employment_type=as_string(item.get("timeType")) or None,
                    description=item.get("description") or item.get("jobDescription"),
                    workplace_type=detect_workplace_type(location_text),
                    job_url=external_path,
                    apply_url=external_path,
                    posted_at=_parse_datetime(
                        item.get("postedOn") or item.get("postedDate")
                    ),
                    raw_payload=item,
                )
            )
        return jobs


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    for key in ("jobPostings", "jobs", "positions"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
