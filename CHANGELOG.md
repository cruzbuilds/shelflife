# Changelog

Versions follow [semantic versioning](https://semver.org/). Anything before 1.0 may change the inventory format or the command line between minor versions, and this file will say so.

## 0.1.0 - 2026-09-14

First release. Everything in [engagement/03-scope.md](engagement/03-scope.md) is built; the two additions made along the way (JSON input, `--offline`) were re-confirmed in that document on the day of this release.

- Inventory file in YAML or JSON: every item has a name, a type, and an owner, plus either a `check` block for live types or an `expires` date. Validation refuses anything ambiguous.
- Live check for TLS certificates: real handshake, expiry read off the raw certificate, no chain verification so expired and self-signed certificates still report ([ADR 0003](docs/decisions/0003-tls-checker-does-not-verify.md)).
- Live check for domain registrations via RDAP through the rdap.org redirector ([ADR 0004](docs/decisions/0004-rdap-via-redirector.md)); TLDs without RDAP get a clear message.
- `shelflife check` with a table or `--json` report, `--days` window (default 30), `--offline` to skip live checks.
- Exit codes as a contract: `0` fine, `1` expiring or expired, `2` could not check; `1` outranks `2` ([ADR 0002](docs/decisions/0002-exit-codes.md)).
- `--webhook` / `SHELFLIFE_WEBHOOK`: POST the JSON report when the exit code is 1 or 2, with a one-line summary Slack and Discord render; `--webhook-always` for a heartbeat.
- Redirects followed only to public HTTPS hosts, for both RDAP and the webhook.
- Every pull request reviewed by the [agentic-swarm](https://github.com/cruzbuilds/agentic-swarm); findings in [docs/review-log.md](docs/review-log.md).

The project was called expiry-tracker until the day of this release.
