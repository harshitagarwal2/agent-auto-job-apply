# agent-auto-job-apply

`agent-auto-job-apply` is a local-first Python job discovery and assisted application system.

The repository ships a CLI package named `jobflow-local` for daily US job discovery, deduplication, ranking, review, and guarded application prep.

This v1 is intentionally honest about its boundaries:

- **Greenhouse** and **Lever** are the only apply-capable source families in code.
- **LinkedIn** and **Glassdoor** are **discovery-only/manual-lead** sources.
- **Ashby** and **Workday** are discovery-focused adapters for public JSON feeds or exported fixtures.
- **Default behavior is safe**: local SQLite storage, no secrets required, and no live submissions unless you explicitly enable and configure them.

## What it does

- Sync public job feeds or local fixture exports into SQLite
- Canonicalize jobs across sources and deduplicate matching postings
- Rank jobs against a configurable US-focused role profile
- Keep a review queue with approve/reject/defer decisions
- Record dry-run application attempts in a local ledger

## What it does not do

- It does **not** bypass anti-bot controls
- It does **not** automate LinkedIn or Glassdoor submissions
- It does **not** claim universal auto-apply support
- It does **not** require API keys or profile secrets for basic sync/list/review/test workflows

## Quick start

Python 3.12+ is required.

### Quick setup — if you've done this kind of thing before

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
cp jobflow.example.toml jobflow.toml
```

Then enable the sources you want in `jobflow.toml`, and only after that run:

```bash
jobflow sync --config jobflow.toml
jobflow list --config jobflow.toml
jobflow review --config jobflow.toml
```

### First run with Claude Code (recommended)

```bash
git clone https://github.com/harshitagarwal2/agent-auto-job-apply.git
cd agent-auto-job-apply
./scripts/claude/bootstrap.sh
```

That wrapper:

- creates `.venv/` if needed
- installs the repo in editable mode with dev dependencies
- creates `jobflow.toml` if it does not already exist

Then edit `jobflow.toml` and enable the sources you actually want.

### No-secrets smoke test

If you want a deterministic first run before adding real company boards or personal lead exports:

```bash
JOBFLOW_CONFIG=jobflow.smoke.toml ./scripts/claude/sync.sh
JOBFLOW_CONFIG=jobflow.smoke.toml ./scripts/claude/list.sh --limit 10
```

`jobflow.smoke.toml` uses checked-in fixture feeds, so it always returns sample jobs without secrets or personal data.

To create a starter config without copying by hand:

```bash
jobflow init-config --path jobflow.toml
```

If you are operating through Claude Code, prefer the wrapper instead:

```bash
./scripts/claude/init-config.sh
```

For a fresh clone, prefer `./scripts/claude/bootstrap.sh` because the wrapper scripts require the repo-local `.venv/bin/jobflow` binary.

## Claude Code operator workflow

This repo now includes a Claude Code operator layer that sits on top of the existing `jobflow` CLI.

- `CLAUDE.md` stores the project memory and safety rules Claude should load at session start.
- `.claude/settings.json` grants wrapper-first permissions so routine work goes through checked-in scripts.
- `.claude/skills/` contains the reusable daily-ops, queue-review, and guarded-apply skills.
- `scripts/claude/*.sh` are the preferred entrypoints for setup, sync, listing, review, dry-run apply, and live apply.

If `jobflow.toml` does not exist yet, initialize the repo first:

```bash
./scripts/claude/bootstrap.sh
```

If the environment already exists and you only need to recreate config, use `./scripts/claude/init-config.sh`.

Typical Claude-driven flow:

```bash
./scripts/claude/sync.sh
./scripts/claude/list.sh --limit 25
./scripts/claude/review.sh
./scripts/claude/apply-dry-run.sh --job-id <job-id>
```

Live apply stays opt-in and guarded. Use it only after a successful dry run, only for Greenhouse or Lever, and only when all of the following are true:

- `[apply].allow_live_submit = true`
- the chosen source sets `apply_mode = "live_opt_in"`
- the chosen source sets `allow_live_apply = true`
- `api_key_env` is configured and the named environment variable is set
- you use the checked-in wrapper plus an exact job-id confirmation

```bash
./scripts/claude/apply-live.sh --job-id <job-id> --confirm-job-id <job-id>
```

If `jobflow.toml` is missing, the operational wrappers fail closed and tell you how to create it.

## CLI commands

### Sync configured sources

```bash
jobflow sync --config jobflow.toml
```

### List ranked jobs

```bash
jobflow list --config jobflow.toml --limit 25
```

### Review queue

Show pending review items:

```bash
jobflow review --config jobflow.toml
```

Mark a decision:

```bash
jobflow review --config jobflow.toml --job-id <job-id> --decision approved --notes "Strong match"
```

### Application dry-run

```bash
jobflow apply-dry-run --config jobflow.toml --job-id <job-id>
```

That command **does not submit** anything. It validates policy, prepares the provider-specific request preview when allowed, and writes a ledger row locally.

### Live application (guarded)

```bash
jobflow apply-live --config jobflow.toml --job-id <job-id> --confirm-job-id <job-id>
```

This command delegates to the same `ApplyService` used for dry runs, but with `dry_run=False`. It remains guarded by the existing policy checks, provider credential requirements, and an explicit confirmation that must exactly match the target job id.

## Supported source families

| Family | Discovery | Apply path in code | Notes |
| --- | --- | --- | --- |
| Greenhouse | Yes | Yes, guarded | Public board discovery; live submit requires authenticated API usage |
| Lever | Yes | Yes, guarded | Public postings discovery; live submit requires API key |
| Ashby | Yes | No | JSON-feed/export driven v1 adapter |
| Workday | Yes | No | JSON-feed/export driven v1 adapter |
| LinkedIn | Yes | No | Manual-lead/discovery only |
| Glassdoor | Yes | No | Manual-lead/discovery only |

## Configuration

See `jobflow.example.toml` for a starter example. Relative paths are resolved from the config file directory.

Supporting local files included in the repo:

- `jobflow.smoke.toml` — safe smoke-test config using checked-in fixtures
- `.env.example` — example variable names for optional live-apply credentials
- `manual/README.md` — manual/export feed formats and copy-ready sample files

Recommended first sources for real daily usage:

- Greenhouse boards for target companies
- Lever sites for target companies
- Ashby and Workday exports or JSON feeds where available
- LinkedIn and Glassdoor as manual-lead files or assisted discovery inputs

## Repository docs

- `docs/ARCHITECTURE.md` — system layout and data flow
- `docs/CLAUDE_CODE.md` — Claude operator runbook, task recipes, and safety policy
- `docs/OPERATIONS.md` — daily operator workflow
- `docs/SOURCE_POLICY.md` — source-family boundaries and safety rules
- `CONTRIBUTING.md` — local development and contribution expectations

## What still needs your real data

The repo is now polished for setup and dry-run operation, but a real daily workflow still needs your own inputs:

- target companies or real Greenhouse/Lever board identifiers
- optional manual/export JSON feeds under `manual/`
- optional live-apply API keys via environment variables from `.env.example`
- your personal resume/application facts if you want real submit-ready payloads

## Tests

```bash
pytest
```

The included tests prove:

- policy blocking for non-apply-capable families
- live-apply confirmation and credential guards
- deduplication across source families
- idempotent sync behavior

## License

MIT — see `LICENSE`.
