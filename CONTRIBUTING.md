# Contributing

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
pytest
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
