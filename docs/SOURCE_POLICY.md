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
