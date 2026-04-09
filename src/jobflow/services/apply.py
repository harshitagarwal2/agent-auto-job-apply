from __future__ import annotations

import os
from base64 import b64encode
from pathlib import Path
from typing import Any

import httpx

from jobflow.domain import (
    AppConfig,
    ApplicantProfile,
    ApplyPreview,
    SourceConfig,
    SourceFamily,
)
from jobflow.policies import PolicyViolation, ensure_can_apply
from jobflow.repository import JobRepository


class ApplyService:
    def __init__(self, repo: JobRepository) -> None:
        self.repo = repo

    def apply(
        self,
        *,
        config: AppConfig,
        base_dir: Path,
        job_id: str,
        profile: ApplicantProfile | None = None,
        dry_run: bool = True,
    ) -> ApplyPreview:
        del base_dir
        profile = profile or ApplicantProfile()
        job = self.repo.get_job(job_id)
        if job is None:
            raise KeyError(f"Job not found: {job_id}")

        source_record, source_config = self._select_source(
            job_id, config, dry_run=dry_run
        )
        try:
            ensure_can_apply(source_config, config.apply, dry_run=dry_run)
            if source_config.family == SourceFamily.GREENHOUSE:
                preview = _greenhouse_preview(
                    source_config, source_record.external_id, profile, dry_run
                )
            elif source_config.family == SourceFamily.LEVER:
                preview = _lever_preview(
                    source_config, source_record.external_id, profile, dry_run
                )
            else:
                preview = self._blocked_preview(
                    source=source_config,
                    dry_run=dry_run,
                    note=f"{source_config.family.value} is not apply-capable in v1",
                )
        except PolicyViolation as exc:
            preview = self._blocked_preview(
                source=source_config,
                dry_run=dry_run,
                note=str(exc),
            )

        preview.job_id = job.id
        preview.source_name = source_config.name
        self.repo.record_application(preview)
        return preview

    def _blocked_preview(
        self, *, source: SourceConfig, dry_run: bool, note: str
    ) -> ApplyPreview:
        return ApplyPreview(
            status="blocked",
            job_id="",
            source_name="",
            family=source.family,
            dry_run=dry_run,
            endpoint=None,
            note=note,
        )

    def _select_source(self, job_id: str, config: AppConfig, *, dry_run: bool):
        source_records = self.repo.get_sources_for_job(job_id)
        config_by_name = {source.name: source for source in config.sources}

        if not source_records:
            raise RuntimeError(f"No source records found for job {job_id}")

        indexed_sources: list[tuple[int, Any, SourceConfig]] = []
        for index, configured_source in enumerate(config.sources):
            matching_records = [
                record
                for record in source_records
                if record.source_name == configured_source.name
            ]
            for record in matching_records:
                indexed_sources.append((index, record, configured_source))

        for record in sorted(
            source_records, key=lambda item: (item.source_name, item.id)
        ):
            if record.source_name in config_by_name:
                continue
            raise RuntimeError(f"Source config '{record.source_name}' is missing")

        if not indexed_sources:
            raise RuntimeError(f"No configured sources found for job {job_id}")

        ordered_candidates = sorted(
            indexed_sources,
            key=lambda item: (item[0], item[1].source_name, item[1].id),
        )

        for _, record, configured_source in ordered_candidates:
            try:
                ensure_can_apply(configured_source, config.apply, dry_run=dry_run)
                return record, configured_source
            except PolicyViolation:
                continue

        _, record, configured_source = ordered_candidates[0]
        return record, configured_source


def _greenhouse_preview(
    source: SourceConfig,
    external_id: str,
    profile: ApplicantProfile,
    dry_run: bool,
) -> ApplyPreview:
    endpoint = f"https://boards-api.greenhouse.io/v1/boards/{source.board_token}/jobs/{external_id}"
    payload = {
        "first_name": profile.first_name or "<required>",
        "last_name": profile.last_name or "<required>",
        "email": profile.email or "<required>",
        "phone": profile.phone or "<optional>",
        "resume_text": "<required or resume upload>",
        "comments": profile.comments or "",
    }

    if dry_run:
        return ApplyPreview(
            status="dry_run_ready",
            job_id="",
            source_name="",
            family=SourceFamily.GREENHOUSE,
            dry_run=True,
            endpoint=endpoint,
            payload_preview=payload,
            note="Preview only. Greenhouse live submission requires authenticated Job Board API usage and should be proxied safely.",
        )

    api_key = _require_api_key(source)
    response = _post_greenhouse(endpoint, api_key=api_key, payload=payload)
    return ApplyPreview(
        status="submitted",
        job_id="",
        source_name="",
        family=SourceFamily.GREENHOUSE,
        dry_run=False,
        endpoint=endpoint,
        payload_preview=payload,
        response_preview=response,
    )


def _lever_preview(
    source: SourceConfig,
    external_id: str,
    profile: ApplicantProfile,
    dry_run: bool,
) -> ApplyPreview:
    domain = "api.eu.lever.co" if source.region.lower() == "eu" else "api.lever.co"
    endpoint = f"https://{domain}/v0/postings/{source.site}/{external_id}"
    payload = {
        "name": " ".join(
            part for part in [profile.first_name, profile.last_name] if part
        ).strip()
        or "<required>",
        "email": profile.email or "<required>",
        "phone": profile.phone or "<optional>",
        "org": profile.current_company or "<optional>",
        "urls": profile.links,
        "comments": profile.comments or "",
    }

    if dry_run:
        return ApplyPreview(
            status="dry_run_ready",
            job_id="",
            source_name="",
            family=SourceFamily.LEVER,
            dry_run=True,
            endpoint=endpoint,
            payload_preview=payload,
            note="Preview only. Lever live submission requires a posting API key and retry-safe rate-limit handling.",
        )

    api_key = _require_api_key(source)
    response = _post_lever(endpoint, api_key=api_key, payload=payload)
    return ApplyPreview(
        status="submitted",
        job_id="",
        source_name="",
        family=SourceFamily.LEVER,
        dry_run=False,
        endpoint=endpoint,
        payload_preview=payload,
        response_preview=response,
    )


def _require_api_key(source: SourceConfig) -> str:
    if not source.api_key_env:
        raise PolicyViolation("live apply requires api_key_env in source config")
    api_key = os.environ.get(source.api_key_env)
    if not api_key:
        raise PolicyViolation(f"environment variable '{source.api_key_env}' is not set")
    return api_key


def _post_greenhouse(
    endpoint: str, *, api_key: str, payload: dict[str, Any]
) -> dict[str, Any]:
    token = b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=20.0, headers=headers) as client:
        response = client.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()


def _post_lever(
    endpoint: str, *, api_key: str, payload: dict[str, Any]
) -> dict[str, Any]:
    with httpx.Client(timeout=20.0) as client:
        try:
            response = client.post(endpoint, params={"key": api_key}, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise PolicyViolation(
                "lever live apply request failed; credential-bearing URLs are not echoed in errors"
            ) from exc
