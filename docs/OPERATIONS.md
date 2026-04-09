# Operations Guide

## Daily workflow

1. Update `jobflow.toml` with the sources you actually want enabled.
2. Run:

```bash
jobflow sync --config jobflow.toml
jobflow list --config jobflow.toml --limit 25
jobflow review --config jobflow.toml
```

3. Approve or reject jobs from the review queue.
4. Use `jobflow apply-dry-run --job-id <id>` to preview provider-specific apply payloads.
5. Only enable live submission after you have validated the source config, credentials, and downstream provider behavior.

## Recommended source strategy

- Use Greenhouse and Lever as the primary structured sources.
- Use Ashby and Workday where you have reliable feeds or exports.
- Treat LinkedIn and Glassdoor as lead surfaces, not unattended submission targets.

## Local data

- SQLite database: `.local/jobflow.sqlite3`
- Per-user config: `jobflow.toml`
- Manual lead files: configurable JSON paths in `jobflow.toml`
