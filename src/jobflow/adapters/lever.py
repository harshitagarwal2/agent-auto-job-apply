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


class LeverAdapter(BaseDiscoveryAdapter):
    def discover(
        self,
        source: SourceConfig,
        *,
        base_dir: Path,
        timeout_seconds: float,
    ) -> list[CanonicalJob]:
        default_url = None
        if source.site:
            domain = (
                "api.eu.lever.co" if source.region.lower() == "eu" else "api.lever.co"
            )
            default_url = f"https://{domain}/v0/postings/{source.site}?mode=json"
        payload = self.load_payload(
            source,
            base_dir=base_dir,
            timeout_seconds=timeout_seconds,
            default_url=default_url,
        )
        jobs: list[CanonicalJob] = []
        for item in payload:
            categories = item.get("categories", {})
            location_text = as_string(
                categories.get("location"), default="United States"
            )
            workplace_hint = as_string(item.get("workplaceType"))
            jobs.append(
                CanonicalJob(
                    source_name=source.name,
                    family=source.family,
                    external_id=as_string(item.get("id")),
                    company=source.company_fallback(),
                    title=as_string(item.get("text")),
                    location_text=location_text,
                    location_country=infer_country(location_text, item.get("country")),
                    employment_type=as_string(categories.get("commitment")) or None,
                    description=item.get("descriptionPlain") or item.get("description"),
                    workplace_type=detect_workplace_type(location_text, workplace_hint),
                    job_url=as_string(item.get("hostedUrl")),
                    apply_url=as_string(item.get("applyUrl")),
                    posted_at=_parse_datetime(
                        item.get("createdAt") or item.get("updatedAt")
                    ),
                    metadata={"board_ref": source.site, "team": categories.get("team")},
                    raw_payload=item,
                )
            )
        return jobs


def _parse_datetime(value: str | int | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, int):
        return datetime.fromtimestamp(value / 1000)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
