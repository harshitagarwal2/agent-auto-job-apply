from __future__ import annotations

from pathlib import Path

from jobflow.adapters.base import BaseDiscoveryAdapter
from jobflow.domain import CanonicalJob, SourceConfig, WorkplaceType


class GlassdoorAdapter(BaseDiscoveryAdapter):
    def discover(
        self,
        source: SourceConfig,
        *,
        base_dir: Path,
        timeout_seconds: float,
    ) -> list[CanonicalJob]:
        if source.manual_leads:
            leads = source.manual_leads
        else:
            payload = self.load_payload(
                source, base_dir=base_dir, timeout_seconds=timeout_seconds
            )
            leads = payload

        jobs: list[CanonicalJob] = []
        for lead in leads:
            payload = lead.model_dump() if hasattr(lead, "model_dump") else dict(lead)
            jobs.append(
                CanonicalJob(
                    source_name=source.name,
                    family=source.family,
                    external_id=payload["external_id"],
                    company=payload["company"],
                    title=payload["title"],
                    location_text=payload.get("location_text", "United States"),
                    location_country=payload.get("location_country", "US"),
                    description=payload.get("description"),
                    workplace_type=WorkplaceType.UNSPECIFIED,
                    job_url=payload["job_url"],
                    apply_url=payload.get("apply_url") or payload["job_url"],
                    posted_at=payload.get("posted_at"),
                    metadata={"manual_lead": True},
                    raw_payload=payload,
                )
            )
        return jobs
