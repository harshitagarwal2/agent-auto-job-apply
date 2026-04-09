from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

from jobflow.domain import CanonicalJob, SourceConfig, WorkplaceType


class BaseDiscoveryAdapter(ABC):
    @abstractmethod
    def discover(
        self,
        source: SourceConfig,
        *,
        base_dir: Path,
        timeout_seconds: float,
    ) -> list[CanonicalJob]:
        raise NotImplementedError

    def load_payload(
        self,
        source: SourceConfig,
        *,
        base_dir: Path,
        timeout_seconds: float,
        default_url: str | None = None,
    ) -> Any:
        feed_path = source.resolved_feed_path(base_dir)
        if feed_path is not None:
            return json.loads(feed_path.read_text())

        url = source.jobs_url or default_url
        if url is None:
            raise ValueError(f"Source '{source.name}' is missing feed_path or jobs_url")

        headers = {"User-Agent": "jobflow-local/0.1"}
        headers.update(source.headers)
        with httpx.Client(
            timeout=timeout_seconds, follow_redirects=True, headers=headers
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()


def detect_workplace_type(
    location_text: str, workplace_hint: str | None = None
) -> WorkplaceType:
    blob = f"{location_text} {workplace_hint or ''}".lower()
    if "remote" in blob:
        return WorkplaceType.REMOTE
    if "hybrid" in blob:
        return WorkplaceType.HYBRID
    if "on-site" in blob or "onsite" in blob:
        return WorkplaceType.ON_SITE
    return WorkplaceType.UNSPECIFIED


def infer_country(
    location_text: str, explicit_country: str | None = None
) -> str | None:
    if explicit_country:
        return explicit_country
    lowered = location_text.lower()
    if "united states" in lowered or " usa" in lowered or lowered.endswith(" us"):
        return "US"
    return None


def as_string(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)
