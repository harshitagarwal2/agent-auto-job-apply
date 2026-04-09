---
name: jobflow-queue-review
description: Review, approve, reject, or defer jobs from the queue through the checked-in review wrapper when the user asks to work triage decisions.
---

# Jobflow queue review

Use this skill when the user wants to inspect the pending queue or store review decisions.

## Required sequence

1. Run `./scripts/claude/review.sh` to inspect pending items unless the user already named a specific job id.
2. Summarize the queue before changing review state.
3. When the user gives a decision, run `./scripts/claude/review.sh --job-id <job-id> --decision approved|rejected|deferred` and include `--notes` only when the user supplied or approved the note.
4. Re-run `./scripts/claude/review.sh` or `./scripts/claude/list.sh` if you need to confirm the updated state.

## Guardrails

- Do not invent review notes.
- Keep review actions separate from apply actions.
- If the user wants to move from review to apply, use the guarded apply skill next.
