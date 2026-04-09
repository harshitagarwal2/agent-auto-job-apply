# Claude Code Operator Guide

This repository supports Claude Code as the orchestration layer for the existing `jobflow` CLI. Claude should drive the workflow through the checked-in wrappers and skills, while the Python application remains the system of record for discovery, review, policy enforcement, and application ledger writes.

## Operator files

- `CLAUDE.md` — project memory and guardrails loaded at session start
- `.claude/settings.json` — shared Claude Code permissions for this repo
- `.claude/skills/` — reusable daily-ops, queue-review, and guarded-apply skills
- `scripts/claude/` — wrapper scripts Claude should use first

## First-time setup

If the repo does not have a `jobflow.toml` yet, initialize it through the wrapper:

```bash
./scripts/claude/init-config.sh
```

Then edit the generated config to enable the sources and policies you actually want.

## Daily runbook

1. Make sure `jobflow.toml` exists at the repo root.
2. Refresh the database:

```bash
./scripts/claude/sync.sh
```

3. Inspect the ranked queue:

```bash
./scripts/claude/list.sh --limit 25
```

4. Work the review queue:

```bash
./scripts/claude/review.sh
./scripts/claude/review.sh --job-id <job-id> --decision approved --notes "Strong fit"
```

5. Prepare an application preview:

```bash
./scripts/claude/apply-dry-run.sh --job-id <job-id>
```

6. Only after an explicit user request and after all guards are satisfied, run the live wrapper:

```bash
./scripts/claude/apply-live.sh --job-id <job-id> --confirm-job-id <job-id>
```

## Task recipes

### Refresh and summarize new jobs

- Use the `jobflow-daily-ops` skill.
- Run `sync.sh`, then `list.sh`.
- Summarize the best matches and the biggest changes since the last run.

### Triage the review queue

- Use the `jobflow-queue-review` skill.
- Start with `review.sh`.
- Store explicit user decisions with `review.sh --job-id ... --decision ...`.

### Prepare a guarded application

- Use the `jobflow-guarded-apply` skill.
- Run a dry run first.
- Keep the preview and any live submission as separate steps.

## Safety policy

- Wrapper-first: prefer `scripts/claude/*.sh` over raw `jobflow` commands.
- Fail closed: if `jobflow.toml` is missing, do not guess or create a partial workflow. Use `./scripts/claude/init-config.sh` or stop.
- Preserve source-family policy: LinkedIn and Glassdoor are discovery-only/manual.
- Preserve app boundaries: `jobflow.policies` remains the policy gate and `ApplyService` remains the execution path.
- Keep live apply opt-in: require config flags, provider credentials, and `--confirm-job-id`.
- No anti-bot automation, browser bypass, CAPTCHA evasion, or hidden-session logic.
