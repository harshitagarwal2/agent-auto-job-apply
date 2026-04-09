# Operations Guide

## Daily workflow

1. If `jobflow.toml` does not exist yet, initialize it with `./scripts/claude/init-config.sh` and then update it with the sources you actually want enabled.
2. Prefer the Claude wrappers for routine operations. They inject `--config jobflow.toml`, fail closed if the config file is missing, and keep Claude on the supported execution path.

```bash
./scripts/claude/sync.sh
./scripts/claude/list.sh --limit 25
./scripts/claude/review.sh
```

Equivalent raw CLI commands still exist, but the wrappers are the recommended Claude Code entrypoints.

3. Approve or reject jobs from the review queue.
4. Use `./scripts/claude/apply-dry-run.sh --job-id <id>` to preview provider-specific apply payloads.
5. Only use live submission after you have validated the source config, credentials, and downstream provider behavior.

## Guarded live-apply checklist

Before running a live apply, confirm all of the following:

- the source family is Greenhouse or Lever
- `[apply].allow_live_submit = true`
- the source policy sets `apply_mode = "live_opt_in"`
- the source policy sets `allow_live_apply = true`
- `api_key_env` is set in config and the named environment variable exists locally
- you are using the wrapper and repeating the exact job id as confirmation

```bash
./scripts/claude/apply-live.sh --job-id <id> --confirm-job-id <id>
```

If any guard is missing, the workflow should fail closed and record a blocked application ledger entry instead of attempting a submit.

## Raw CLI reference

If you are operating without Claude Code, the underlying CLI commands are:

```bash
jobflow sync --config jobflow.toml
jobflow list --config jobflow.toml --limit 25
jobflow review --config jobflow.toml
```

## Recommended source strategy

- Use Greenhouse and Lever as the primary structured sources.
- Use Ashby and Workday where you have reliable feeds or exports.
- Treat LinkedIn and Glassdoor as lead surfaces, not unattended submission targets.

## Local data

- SQLite database: `.local/jobflow.sqlite3`
- Per-user config: `jobflow.toml`
- Manual lead files: configurable JSON paths in `jobflow.toml`
