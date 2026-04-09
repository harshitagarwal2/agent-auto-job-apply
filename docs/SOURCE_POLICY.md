# Source Policy

## Supported source families in v1

| Source family | Discovery | Dry-run apply | Live apply |
| --- | --- | --- | --- |
| Greenhouse | Yes | Yes | Opt-in only |
| Lever | Yes | Yes | Opt-in only |
| Ashby | Yes | No | No |
| Workday | Yes | No | No |
| LinkedIn | Yes | No | No |
| Glassdoor | Yes | No | No |

## Why these limits exist

- LinkedIn and Glassdoor are high-friction, high-churn surfaces and should not be treated as unattended submission targets.
- Greenhouse and Lever have more repeatable public discovery patterns and clearer guarded apply paths.
- Ashby and Workday vary too much to promise broad unattended submission in v1.

## Non-goals

- No CAPTCHA bypass
- No account takeover or hidden-session automation
- No claim of universal auto-apply support

## Claude Code operator policy

The Claude operator layer must preserve the same boundaries as the Python app:

- use `.claude/skills/` and `scripts/claude/*.sh`, not legacy `.claude/commands/`
- prefer wrapper scripts over raw `jobflow` invocations for daily operations
- require explicit live confirmation through `./scripts/claude/apply-live.sh --job-id <job-id> --confirm-job-id <job-id>`
- treat LinkedIn and Glassdoor as discovery-only/manual even when Claude is driving the workflow
- do not add browser bypasses, anti-bot automation, or unsupported provider flows
