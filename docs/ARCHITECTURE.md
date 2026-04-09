# Architecture

## Goal

This project is a local-first job discovery and assisted application workflow for US roles such as software engineer, product manager, program manager, and business analyst.

## System layout

- `src/jobflow/cli.py` — Typer CLI entrypoints
- `src/jobflow/domain.py` — canonical config and job models
- `src/jobflow/db.py` — SQLite schema and persistence primitives
- `src/jobflow/repository.py` — deduplication, review state, application ledger
- `src/jobflow/ranking.py` — role/location scoring
- `src/jobflow/policies.py` — source-family capability and safety rules
- `src/jobflow/adapters/` — discovery adapters per source family
- `src/jobflow/services/sync.py` — daily sync orchestration
- `src/jobflow/services/apply.py` — guarded dry-run/live-apply preparation
- `scripts/claude/` — wrapper scripts Claude Code should prefer for daily operations
- `.claude/skills/` and `CLAUDE.md` — Claude Code operator memory and task skills

## Data flow

1. Source adapters discover jobs or load manual/exported leads.
2. Each job is normalized into `CanonicalJob`.
3. Ranking computes a score against the configured search profile.
4. Repository deduplicates jobs by company, title, and location fingerprint.
5. Review state and application attempts are written to SQLite.
6. Apply flow validates policy before generating a provider-specific preview or live submission.
7. Claude Code should orchestrate through the checked-in wrapper scripts rather than bypassing the CLI directly.

## Safety boundary

- LinkedIn and Glassdoor are discovery-only/manual-lead families.
- Greenhouse and Lever are apply-capable in code, but dry-run by default.
- Ashby and Workday are discovery-focused in v1.
- No anti-bot bypass logic belongs in this repository.
- Live apply remains guarded by config flags, provider credentials, and an explicit confirmation at the CLI layer.
