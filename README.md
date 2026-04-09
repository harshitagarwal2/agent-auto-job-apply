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

### Quick setup — if you've done this kind of thing before

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
cp jobflow.example.toml jobflow.toml
jobflow sync --config jobflow.toml
jobflow list --config jobflow.toml
jobflow review --config jobflow.toml
```

Then enable the sources you want in `jobflow.toml`.

To create a starter config without copying by hand:

```bash
jobflow init-config --path jobflow.toml
```

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

See `jobflow.example.toml` for a fully commented example. Relative paths are resolved from the config file directory.

Recommended first sources for real daily usage:

- Greenhouse boards for target companies
- Lever sites for target companies
- Ashby and Workday exports or JSON feeds where available
- LinkedIn and Glassdoor as manual-lead files or assisted discovery inputs

## Repository docs

- `docs/ARCHITECTURE.md` — system layout and data flow
- `docs/OPERATIONS.md` — daily operator workflow
- `docs/SOURCE_POLICY.md` — source-family boundaries and safety rules
- `CONTRIBUTING.md` — local development and contribution expectations

## Tests

```bash
pytest
```

The included tests prove:

- policy blocking for non-apply-capable families
- deduplication across source families
- idempotent sync behavior

## License

MIT — see `LICENSE`.
