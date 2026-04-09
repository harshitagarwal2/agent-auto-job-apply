from __future__ import annotations

import json
from pathlib import Path

import typer

from jobflow.config import DEFAULT_CONFIG_PATH, EXAMPLE_CONFIG, load_config
from jobflow.db import init_db, make_engine
from jobflow.domain import ApplicantProfile, ReviewStatus, SourceFamily
from jobflow.repository import JobRepository
from jobflow.services.apply import ApplyService
from jobflow.services.sync import SyncService

app = typer.Typer(help="Local-first job discovery and assisted apply workflow")


def _bootstrap(config_path: Path):
    config, base_dir = load_config(config_path, allow_missing=True)
    engine = make_engine(config.resolved_database_path(base_dir))
    init_db(engine)
    repo = JobRepository(engine)
    return config, base_dir, repo


@app.command("init-config")
def init_config(
    path: Path = typer.Option(
        DEFAULT_CONFIG_PATH, help="Where to write the starter config"
    ),
    force: bool = typer.Option(False, help="Overwrite an existing file"),
) -> None:
    if path.exists() and not force:
        raise typer.BadParameter(f"Refusing to overwrite existing config: {path}")
    path.write_text(EXAMPLE_CONFIG)
    typer.echo(f"Wrote starter config to {path}")


@app.command()
def sync(
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH, exists=False, help="Path to config TOML"
    ),
) -> None:
    loaded_config, base_dir, repo = _bootstrap(config)
    stats = SyncService(repo).run(loaded_config, base_dir=base_dir)
    typer.echo(
        json.dumps(
            {
                "sources_seen": stats.sources_seen,
                "jobs_seen": stats.jobs_seen,
                "created": stats.created,
                "updated": stats.updated,
                "deduped": stats.deduped,
                "blocked": stats.blocked,
                "errors": stats.errors,
            },
            indent=2,
        )
    )


@app.command("list")
def list_jobs(
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH, exists=False, help="Path to config TOML"
    ),
    limit: int = typer.Option(20, min=1, help="Maximum jobs to show"),
    review_status: ReviewStatus | None = typer.Option(
        None, help="Filter by review status"
    ),
    family: SourceFamily | None = typer.Option(
        None, help="Filter by primary source family"
    ),
) -> None:
    _, _, repo = _bootstrap(config)
    jobs = repo.list_jobs(
        limit=limit,
        review_status=review_status,
        family=family.value if family else None,
    )
    if not jobs:
        typer.echo("No jobs found")
        return

    for job in jobs:
        typer.echo(
            json.dumps(
                {
                    "id": job.id,
                    "score": job.score,
                    "company": job.company,
                    "title": job.title,
                    "location": job.location_text,
                    "family": job.primary_source_family,
                    "review_status": job.review_status,
                    "job_url": job.job_url,
                    "reasons": job.score_reasons,
                }
            )
        )


@app.command()
def review(
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH, exists=False, help="Path to config TOML"
    ),
    job_id: str | None = typer.Option(None, help="Job id to update"),
    decision: ReviewStatus | None = typer.Option(None, help="Review decision to store"),
    notes: str | None = typer.Option(None, help="Optional review notes"),
    limit: int = typer.Option(
        20, min=1, help="Queue size to show when no job id is given"
    ),
) -> None:
    _, _, repo = _bootstrap(config)

    if job_id and decision:
        job = repo.update_review(job_id, decision, notes)
        typer.echo(
            json.dumps(
                {
                    "id": job.id,
                    "review_status": job.review_status,
                    "review_notes": job.review_notes,
                }
            )
        )
        return

    jobs = repo.list_jobs(limit=limit, review_status=ReviewStatus.PENDING)
    if not jobs:
        typer.echo("No pending review jobs")
        return

    for job in jobs:
        typer.echo(
            json.dumps(
                {
                    "id": job.id,
                    "score": job.score,
                    "company": job.company,
                    "title": job.title,
                    "location": job.location_text,
                    "job_url": job.job_url,
                }
            )
        )


@app.command("apply-dry-run")
def apply_dry_run(
    job_id: str = typer.Option(..., help="Job id to prepare for submission"),
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH, exists=False, help="Path to config TOML"
    ),
) -> None:
    loaded_config, base_dir, repo = _bootstrap(config)
    preview = ApplyService(repo).apply(
        config=loaded_config,
        base_dir=base_dir,
        job_id=job_id,
        profile=ApplicantProfile(),
        dry_run=True,
    )
    typer.echo(preview.model_dump_json(indent=2))


if __name__ == "__main__":  # pragma: no cover
    app()
