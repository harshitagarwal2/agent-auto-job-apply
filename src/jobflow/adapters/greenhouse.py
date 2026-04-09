from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jobflow.adapters.base import (
    BaseDiscoveryAdapter,
    as_string,
    detect_workplace_type,
    infer_country,
)
from jobflow.domain import CanonicalJob, SourceConfig


class GreenhouseAdapter(BaseDiscoveryAdapter):
    def discover(
        self,
        source: SourceConfig,
        *,
        base_dir: Path,
        timeout_seconds: float,
    ) -> list[CanonicalJob]:
        default_url = None
        if source.board_token:
            default_url = f"https://boards-api.greenhouse.io/v1/boards/{source.board_token}/jobs?content=true"
        payload = self.load_payload(
            source,
            base_dir=base_dir,
            timeout_seconds=timeout_seconds,
            default_url=default_url,
        )
        jobs: list[CanonicalJob] = []
        for item in payload.get("jobs", []):
            location_text = as_string(
                item.get("location", {}).get("name"), default="United States"
            )
            posted_at = _parse_datetime(item.get("updated_at"))
            jobs.append(
                CanonicalJob(
                    source_name=source.name,
                    family=source.family,
                    external_id=as_string(item.get("id")),
                    company=source.company_fallback(),
                    title=as_string(item.get("title")),
                    location_text=location_text,
                    location_country=infer_country(location_text),
                    employment_type=None,
                    description=item.get("content"),
                    workplace_type=detect_workplace_type(location_text),
                    job_url=as_string(item.get("absolute_url")),
                    apply_url=as_string(item.get("absolute_url")),
                    posted_at=posted_at,
                    metadata={"board_ref": source.board_token}
                    if source.board_token
                    else {},
                    raw_payload=item,
                )
            )
        return jobs


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
