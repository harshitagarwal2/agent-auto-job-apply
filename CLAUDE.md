# Claude Code project memory

This repository uses Claude Code as an operator layer on top of the existing `jobflow` CLI. Keep the Python app as the execution engine and keep Claude focused on orchestration, review, and safe command sequencing.

## Core operating rules

- Prefer the checked-in wrappers in `scripts/claude/` over raw `jobflow` commands.
- Use project skills from `.claude/skills/`; do not add or rely on legacy `.claude/commands/`.
- `jobflow.toml` at the repo root is the default operator config. If it is missing, fail closed and tell the user to run `./scripts/claude/init-config.sh` or copy `jobflow.example.toml` manually.
- LinkedIn and Glassdoor remain discovery-only/manual. Do not turn them into live apply targets.
- Do not add anti-bot bypasses, browser evasion, CAPTCHA workarounds, or hidden-session automation.

## Safe workflow order

1. `./scripts/claude/sync.sh`
2. `./scripts/claude/list.sh --limit 25`
3. `./scripts/claude/review.sh`
4. `./scripts/claude/apply-dry-run.sh --job-id <job-id>`
5. Only after the dry run is reviewed, use `./scripts/claude/apply-live.sh --job-id <job-id> --confirm-job-id <job-id>`

## First-time setup

If `jobflow.toml` is missing, initialize it through the checked-in wrapper:

1. `./scripts/claude/init-config.sh`
2. Edit `jobflow.toml` to enable the sources you want.
3. Resume the safe workflow order above.

## Live apply guardrails

Live apply is allowed only when all of these are true:

- the job resolves to a supported apply-capable family (`greenhouse` or `lever`)
- `[apply].allow_live_submit = true`
- the chosen source policy sets `apply_mode = "live_opt_in"`
- the chosen source policy sets `allow_live_apply = true`
- the source config sets `api_key_env`
- the named environment variable is present
- the operator repeats the exact job id with `--confirm-job-id`

The CLI command for live submit is intentionally thin and delegates to `ApplyService(dry_run=False)`. Policy checks stay in `jobflow.policies` and apply behavior stays in `jobflow.services.apply`.

## Important files

- `src/jobflow/cli.py` — public CLI entrypoints
- `src/jobflow/services/apply.py` — guarded dry-run and live apply path
- `src/jobflow/policies.py` — source family and live-apply policy enforcement
- `scripts/claude/` — Claude-facing wrappers
- `docs/CLAUDE_CODE.md` — operator runbook, recipes, and safety policy
