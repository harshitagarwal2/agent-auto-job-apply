---
name: jobflow-guarded-apply
description: Prepare or submit a guarded application through the wrapper scripts when the user asks for apply previews or an explicit live apply on a supported source.
---

# Jobflow guarded apply

Use this skill when the user wants an application preview or a live submit.

## Required sequence

1. Identify the target job id.
2. Always run `./scripts/claude/apply-dry-run.sh --job-id <job-id>` first and summarize the preview.
3. Treat live submit as a separate, explicit step. Only proceed when the user clearly asks for live apply after the dry run.
4. For live submit, run `./scripts/claude/apply-live.sh --job-id <job-id> --confirm-job-id <job-id>`.

## Live apply checklist

Before step 4, confirm all of these are true:

- the source family is `greenhouse` or `lever`
- `[apply].allow_live_submit = true`
- the source policy uses `apply_mode = "live_opt_in"`
- the source policy sets `allow_live_apply = true`
- `api_key_env` is configured and the environment variable is set locally

## Guardrails

- Do not use live apply for LinkedIn, Glassdoor, Ashby, or Workday.
- Do not bypass the wrapper scripts.
- Do not call provider endpoints directly.
