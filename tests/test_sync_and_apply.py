from pathlib import Path

from src.jobflow.db import init_db, make_engine
from src.jobflow.domain import AppConfig, DatabaseConfig, SourceConfig, SourceFamily
from src.jobflow.repository import JobRepository
from src.jobflow.services.apply import ApplyService
from src.jobflow.services.sync import SyncService


def _repo_for(tmp_path: Path) -> JobRepository:
    engine = make_engine(tmp_path / "jobflow.sqlite3")
    init_db(engine)
    return JobRepository(engine)


def test_sync_is_idempotent(tmp_path: Path, fixtures_dir: Path) -> None:
    repo = _repo_for(tmp_path)
    config = AppConfig(
        database=DatabaseConfig(path=tmp_path / "jobflow.sqlite3"),
        sources=[
            SourceConfig(
                name="acme-greenhouse",
                family=SourceFamily.GREENHOUSE,
                company="Acme",
                board_token="acme",
                feed_path=Path("greenhouse_jobs.json"),
            )
        ],
    )

    service = SyncService(repo)
    first = service.run(config, base_dir=fixtures_dir)
    second = service.run(config, base_dir=fixtures_dir)

    assert first.created == 1
    assert second.created == 0
    assert second.updated == 1
    assert repo.counts() == (1, 1, 0)


def test_sync_deduplicates_matching_jobs_across_sources(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    repo = _repo_for(tmp_path)
    config = AppConfig(
        database=DatabaseConfig(path=tmp_path / "jobflow.sqlite3"),
        sources=[
            SourceConfig(
                name="acme-greenhouse",
                family=SourceFamily.GREENHOUSE,
                company="Acme",
                board_token="acme",
                feed_path=Path("greenhouse_jobs.json"),
            ),
            SourceConfig(
                name="acme-lever",
                family=SourceFamily.LEVER,
                company="Acme",
                site="acme",
                feed_path=Path("lever_jobs.json"),
            ),
        ],
    )

    stats = SyncService(repo).run(config, base_dir=fixtures_dir)
    jobs = repo.list_jobs(limit=10)

    assert stats.created == 1
    assert stats.deduped == 1
    assert len(jobs) == 1
    assert jobs[0].source_count == 2
    assert repo.counts() == (1, 2, 0)


def test_policy_blocks_discovery_only_apply_attempts(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    repo = _repo_for(tmp_path)
    config = AppConfig(
        database=DatabaseConfig(path=tmp_path / "jobflow.sqlite3"),
        sources=[
            SourceConfig(
                name="linkedin-manual",
                family=SourceFamily.LINKEDIN,
                feed_path=Path("linkedin_manual_leads.json"),
            )
        ],
    )

    SyncService(repo).run(config, base_dir=fixtures_dir)
    job = repo.list_jobs(limit=1)[0]

    preview = ApplyService(repo).apply(
        config=config,
        base_dir=fixtures_dir,
        job_id=job.id,
        dry_run=True,
    )

    assert preview.status == "blocked"
    assert "discovery-only/manual" in (preview.note or "")
    entries = repo.application_entries()
    assert len(entries) == 1
    assert entries[0].status == "blocked"
    assert entries[0].source_family == "linkedin"


def test_greenhouse_apply_dry_run_records_preview(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    repo = _repo_for(tmp_path)
    config = AppConfig(
        database=DatabaseConfig(path=tmp_path / "jobflow.sqlite3"),
        sources=[
            SourceConfig(
                name="acme-greenhouse",
                family=SourceFamily.GREENHOUSE,
                company="Acme",
                board_token="acme",
                feed_path=Path("greenhouse_jobs.json"),
            )
        ],
    )

    SyncService(repo).run(config, base_dir=fixtures_dir)
    job = repo.list_jobs(limit=1)[0]

    preview = ApplyService(repo).apply(
        config=config,
        base_dir=fixtures_dir,
        job_id=job.id,
        dry_run=True,
    )

    assert preview.status == "dry_run_ready"
    assert (
        preview.endpoint == "https://boards-api.greenhouse.io/v1/boards/acme/jobs/101"
    )
    assert preview.payload_preview["email"] == "<required>"
    assert len(repo.application_entries()) == 1
