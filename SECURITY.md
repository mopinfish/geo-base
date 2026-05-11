# Security Policy

We take the security of geo-base seriously. Thank you for taking the time to report a vulnerability responsibly.

## Supported versions

Only the `main` branch is actively maintained. Security fixes are not back-ported to older tags.

## Reporting a vulnerability

**Please do not report security issues in public GitHub issues, pull requests, or discussions.** Public disclosure before a fix is available puts users at risk.

Instead, use one of the following private channels:

1. **GitHub Private Vulnerability Reporting** (preferred) — open a draft advisory at <https://github.com/mopinfish/geo-base/security/advisories/new>. This keeps the report confidential and lets us collaborate on a fix.
2. **Email** — send a description of the issue to `noboru.otsuka@geolonia.com`. Encrypt with our PGP key if you have one (request it via the same address).

Please include:

- A clear description of the issue and its impact (data exposure, privilege escalation, RCE, etc.).
- Steps to reproduce, ideally with a minimal proof of concept.
- The affected component (`api/`, `app/`, `mcp/`, `docker/`, infra config) and the commit hash where you observed the issue.
- Any suggested mitigation, if you have one.

## What to expect

We aim for the following response times, measured from the time we acknowledge your report:

| Severity | First response | Triage decision | Target fix or mitigation |
|---|---|---|---|
| Critical (auth bypass, RCE, data exfiltration) | 1 business day | 3 business days | 14 days |
| High (privilege escalation, sensitive data leak under specific conditions) | 2 business days | 5 business days | 30 days |
| Medium / Low | 5 business days | 10 business days | Best effort, communicated case by case |

If we cannot meet a target, we will let you know and propose a revised timeline.

## Coordinated disclosure

We follow a coordinated disclosure process:

1. You report the issue privately.
2. We confirm the vulnerability and develop a fix.
3. We agree with you on a disclosure timeline (typically aligned with the table above).
4. We release the fix and publish an advisory crediting you, unless you prefer to remain anonymous.

We will not pursue legal action against researchers who:

- Make a good-faith effort to avoid privacy violations, data destruction, and service interruption.
- Give us a reasonable opportunity to investigate and remediate before public disclosure.
- Do not exploit the vulnerability beyond what is necessary to confirm it.

## Out of scope

The following are generally not considered security vulnerabilities for this project:

- Issues that require physical access to a user's device.
- Vulnerabilities in dependencies that are already publicly disclosed and tracked upstream (we welcome PRs that bump the affected dependency).
- Denial-of-service via excessive load on free-tier infrastructure (Fly.io / Vercel / Upstash quotas).
- Self-XSS or social-engineering attacks that require a victim to paste attacker-controlled code into their own browser.
- Issues in development-only code paths gated behind `E2E_MODE=1` or other non-production flags.

## Credits

We maintain a list of researchers who have helped improve geo-base's security in the relevant GitHub Security Advisory. Thank you in advance for keeping our users safe.
