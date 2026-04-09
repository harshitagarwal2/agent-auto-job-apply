# Contributing

## Development setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
pytest
```

For a repo-local smoke check of the Claude operator path:

```bash
JOBFLOW_CONFIG=jobflow.smoke.toml ./scripts/claude/sync.sh
JOBFLOW_CONFIG=jobflow.smoke.toml ./scripts/claude/list.sh --limit 10
```

## Project rules

- Keep the default workflow local-first and dry-run-safe.
- Do not add automated submission for LinkedIn or Glassdoor.
- Treat Greenhouse and Lever as the only v1 apply-capable families.
- Add tests for policy boundaries, deduplication, and idempotent sync when changing core behavior.
- Prefer fixture-driven adapter tests over live network tests.

## Before opening a PR

- Run `pytest`
- Run `python -m compileall src tests`
- Update README or docs when changing user-facing behavior
