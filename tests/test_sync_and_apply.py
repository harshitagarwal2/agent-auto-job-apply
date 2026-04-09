import json
from pathlib import Path
from typing import Optional

from typer.testing import CliRunner

from src.jobflow.cli import app
from src.jobflow.db import init_db, make_engine
from src.jobflow.domain import AppConfig, DatabaseConfig, SourceConfig, SourceFamily
from src.jobflow.repository import JobRepository
from src.jobflow.services.apply import ApplyService
from src.jobflow.services.sync import SyncService


RUNNER = CliRunner()


def _repo_for(tmp_path: Path) -> JobRepository:
    engine = make_engine(tmp_path / "jobflow.sqlite3")
    init_db(engine)
    return JobRepository(engine)


def _write_config(
    tmp_path: Path,
    fixtures_dir: Path,
    *,
    family: SourceFamily,
    allow_live_submit: bool,
    apply_mode: str,
    allow_live_apply: bool,
    api_key_env: Optional[str] = None,
) -> Path:
    db_path = tmp_path / "jobflow.sqlite3"
    feed_path = (
        fixtures_dir / "greenhouse_jobs.json"
        if family == SourceFamily.GREENHOUSE
        else fixtures_dir / "linkedin_manual_leads.json"
    )
    source_name = (
        "acme-greenhouse" if family == SourceFamily.GREENHOUSE else "linkedin-manual"
    )

    lines = [
        "[database]",
        f'path = "{db_path.as_posix()}"',
        "",
        "[apply]",
        f"allow_live_submit = {'true' if allow_live_submit else 'false'}",
        'default_source_tag = "jobflow-local"',
        "",
        "[[sources]]",
        f'name = "{source_name}"',
        f'family = "{family.value}"',
        "enabled = true",
        f'feed_path = "{feed_path.as_posix()}"',
    ]

    if family == SourceFamily.GREENHOUSE:
        lines.extend(['company = "Acme"', 'board_token = "acme"'])

    if api_key_env is not None:
        lines.append(f'api_key_env = "{api_key_env}"')

    lines.extend(
        [
            "",
            "  [sources.policy]",
            "  discovery_enabled = true",
            f'  apply_mode = "{apply_mode}"',
            f"  allow_live_apply = {'true' if allow_live_apply else 'false'}",
        ]
    )

    config_path = tmp_path / "jobflow.toml"
    config_path.write_text("\n".join(lines) + "\n")
    return config_path


def _sync_job_from_cli(tmp_path: Path, config_path: Path) -> tuple[JobRepository, str]:
    result = RUNNER.invoke(app, ["sync", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    repo = _repo_for(tmp_path)
    job = repo.list_jobs(limit=1)[0]
    return repo, job.id


def _write_dual_source_config(
    tmp_path: Path,
    fixtures_dir: Path,
    *,
    greenhouse_apply_mode: str,
    greenhouse_allow_live_apply: bool,
    lever_apply_mode: str,
    lever_allow_live_apply: bool,
    lever_api_key_env: Optional[str] = None,
) -> Path:
    db_path = tmp_path / "jobflow.sqlite3"
    lines = [
        "[database]",
        f'path = "{db_path.as_posix()}"',
        "",
        "[apply]",
        "allow_live_submit = true",
        'default_source_tag = "jobflow-local"',
        "",
        "[[sources]]",
        'name = "acme-greenhouse"',
        'family = "greenhouse"',
        "enabled = true",
        'company = "Acme"',
        'board_token = "acme"',
        f'feed_path = "{(fixtures_dir / "greenhouse_jobs.json").as_posix()}"',
        "",
        "  [sources.policy]",
        "  discovery_enabled = true",
        f'  apply_mode = "{greenhouse_apply_mode}"',
        f"  allow_live_apply = {'true' if greenhouse_allow_live_apply else 'false'}",
        "",
        "[[sources]]",
        'name = "acme-lever"',
        'family = "lever"',
        "enabled = true",
        'company = "Acme"',
        'site = "acme"',
        f'feed_path = "{(fixtures_dir / "lever_jobs.json").as_posix()}"',
    ]

    if lever_api_key_env is not None:
        lines.append(f'api_key_env = "{lever_api_key_env}"')

    lines.extend(
        [
            "",
            "  [sources.policy]",
            "  discovery_enabled = true",
            f'  apply_mode = "{lever_apply_mode}"',
            f"  allow_live_apply = {'true' if lever_allow_live_apply else 'false'}",
        ]
    )

    config_path = tmp_path / "jobflow.toml"
    config_path.write_text("\n".join(lines) + "\n")
    return config_path


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


def test_cli_sync_fails_closed_for_missing_config_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.toml"

    result = RUNNER.invoke(app, ["sync", "--config", str(missing_path)])

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert f"Config file not found: {missing_path}" in result.output


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


def test_apply_live_requires_matching_confirmation(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    config_path = _write_config(
        tmp_path,
        fixtures_dir,
        family=SourceFamily.GREENHOUSE,
        allow_live_submit=True,
        apply_mode="live_opt_in",
        allow_live_apply=True,
        api_key_env="JOBFLOW_GREENHOUSE_API_KEY",
    )
    repo, job_id = _sync_job_from_cli(tmp_path, config_path)

    result = RUNNER.invoke(
        app,
        [
            "apply-live",
            "--config",
            str(config_path),
            "--job-id",
            job_id,
            "--confirm-job-id",
            "not-the-job-id",
        ],
    )

    assert result.exit_code != 0
    assert "--confirm-job-id must exactly match --job-id" in result.output
    assert repo.application_entries() == []


def test_apply_live_blocks_when_live_submit_is_not_enabled(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    config_path = _write_config(
        tmp_path,
        fixtures_dir,
        family=SourceFamily.GREENHOUSE,
        allow_live_submit=False,
        apply_mode="dry_run_only",
        allow_live_apply=False,
    )
    repo, job_id = _sync_job_from_cli(tmp_path, config_path)

    result = RUNNER.invoke(
        app,
        [
            "apply-live",
            "--config",
            str(config_path),
            "--job-id",
            job_id,
            "--confirm-job-id",
            job_id,
        ],
    )

    assert result.exit_code == 0, result.output
    preview = json.loads(result.output)
    assert preview["status"] == "blocked"
    assert "live apply is disabled" in preview["note"]
    entries = repo.application_entries()
    assert len(entries) == 1
    assert entries[0].requested_mode == "live"
    assert entries[0].status == "blocked"


def test_apply_live_blocks_discovery_only_sources(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    config_path = _write_config(
        tmp_path,
        fixtures_dir,
        family=SourceFamily.LINKEDIN,
        allow_live_submit=True,
        apply_mode="disabled",
        allow_live_apply=False,
    )
    repo, job_id = _sync_job_from_cli(tmp_path, config_path)

    result = RUNNER.invoke(
        app,
        [
            "apply-live",
            "--config",
            str(config_path),
            "--job-id",
            job_id,
            "--confirm-job-id",
            job_id,
        ],
    )

    assert result.exit_code == 0, result.output
    preview = json.loads(result.output)
    assert preview["status"] == "blocked"
    assert "discovery-only/manual" in preview["note"]
    entries = repo.application_entries()
    assert len(entries) == 1
    assert entries[0].source_family == "linkedin"
    assert entries[0].requested_mode == "live"


def test_apply_live_blocks_when_provider_credentials_are_missing(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    config_path = _write_config(
        tmp_path,
        fixtures_dir,
        family=SourceFamily.GREENHOUSE,
        allow_live_submit=True,
        apply_mode="live_opt_in",
        allow_live_apply=True,
        api_key_env="JOBFLOW_GREENHOUSE_API_KEY",
    )
    repo, job_id = _sync_job_from_cli(tmp_path, config_path)

    result = RUNNER.invoke(
        app,
        [
            "apply-live",
            "--config",
            str(config_path),
            "--job-id",
            job_id,
            "--confirm-job-id",
            job_id,
        ],
    )

    assert result.exit_code == 0, result.output
    preview = json.loads(result.output)
    assert preview["status"] == "blocked"
    assert "JOBFLOW_GREENHOUSE_API_KEY" in preview["note"]
    entries = repo.application_entries()
    assert len(entries) == 1
    assert entries[0].requested_mode == "live"
    assert entries[0].status == "blocked"


def test_apply_live_prefers_deterministic_eligible_source_for_deduped_jobs(
    tmp_path: Path, fixtures_dir: Path
) -> None:
    config_path = _write_dual_source_config(
        tmp_path,
        fixtures_dir,
        greenhouse_apply_mode="dry_run_only",
        greenhouse_allow_live_apply=False,
        lever_apply_mode="live_opt_in",
        lever_allow_live_apply=True,
        lever_api_key_env="JOBFLOW_LEVER_API_KEY",
    )
    repo, job_id = _sync_job_from_cli(tmp_path, config_path)

    result = RUNNER.invoke(
        app,
        [
            "apply-live",
            "--config",
            str(config_path),
            "--job-id",
            job_id,
            "--confirm-job-id",
            job_id,
        ],
    )

    assert result.exit_code == 0, result.output
    preview = json.loads(result.output)
    assert preview["family"] == "lever"
    assert preview["source_name"] == "acme-lever"
    assert "JOBFLOW_LEVER_API_KEY" in preview["note"]


def test_embedded_init_config_matches_repo_example() -> None:
    from src.jobflow import config as config_module

    assert config_module.EXAMPLE_CONFIG_PATH.exists()
    assert config_module.EXAMPLE_CONFIG == config_module.EXAMPLE_CONFIG_PATH.read_text()
