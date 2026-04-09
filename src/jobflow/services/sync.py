from __future__ import annotations

from pathlib import Path

from jobflow.adapters import ADAPTERS
from jobflow.domain import AppConfig, SyncStats
from jobflow.policies import resolve_policy
from jobflow.ranking import rank_job
from jobflow.repository import JobRepository


class SyncService:
    def __init__(self, repo: JobRepository) -> None:
        self.repo = repo

    def run(self, config: AppConfig, *, base_dir: Path) -> SyncStats:
        stats = SyncStats()
        for source in config.sources:
            policy = resolve_policy(source, config.apply)
            if not policy.discovery_enabled:
                stats.blocked += 1
                continue

            adapter = ADAPTERS[source.family]
            stats.sources_seen += 1
            try:
                jobs = adapter.discover(
                    source,
                    base_dir=base_dir,
                    timeout_seconds=config.request_timeout_seconds,
                )
            except Exception as exc:  # pragma: no cover - exercised by CLI usage
                stats.errors.append(f"{source.name}: {exc}")
                continue

            for job in jobs:
                ranked = rank_job(job, config.profile)
                outcome = self.repo.upsert_job(
                    job, score=ranked.score, reasons=ranked.reasons
                )
                stats.jobs_seen += 1
                stats.created += int(outcome.created)
                stats.updated += int(outcome.updated)
                stats.deduped += int(outcome.deduped)

        return stats
