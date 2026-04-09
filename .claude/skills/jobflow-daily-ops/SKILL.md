---
name: jobflow-daily-ops
description: Run the normal daily sync and shortlist workflow through the checked-in Claude wrappers when the user asks to refresh jobs, scan the queue, or summarize what is new.
---

# Jobflow daily ops

Use this skill for the routine operator loop.

## Required sequence

1. Confirm the repo is bootstrapped. If `.venv/bin/jobflow` or `jobflow.toml` is missing, stop and tell the user to run `./scripts/claude/bootstrap.sh`. If only the config is missing and the environment already exists, `./scripts/claude/init-config.sh` is acceptable.
2. Run `./scripts/claude/sync.sh`.
3. Run `./scripts/claude/list.sh --limit 25` unless the user requested a different limit or filter.
4. Summarize the highest-signal jobs and call out anything that should move to review.

## Guardrails

- Prefer `scripts/claude/*.sh` over raw `jobflow` commands.
- Do not claim that a dry run or live application happened unless you actually ran the matching wrapper.
- Keep LinkedIn and Glassdoor framed as discovery/manual sources.
