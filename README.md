# shelflife

[![CI](https://github.com/cruzbuilds/shelflife/actions/workflows/ci.yml/badge.svg)](https://github.com/cruzbuilds/shelflife/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Reviewed by agentic-review-swarm](https://img.shields.io/badge/reviewed%20by-agentic--review--swarm-8A2BE2)](docs/review-log.md)

Everything you own has a shelf life. This is the one place that knows all of them, and tells you before one runs out.

[Install](#running-it) • [The inventory](#the-inventory) • [Reading the report](#reading-the-report) • [Webhook](#getting-the-report-somewhere-people-look) • [When not to use this](#when-not-to-use-this) • [Decisions](docs/decisions/)

Certificates, domains, API keys, licenses, contracts. They live in different systems, get tracked by different people, and the one that takes you down is always the one nobody owned. This is a command-line tool that keeps one inventory of all of them, checks the ones it can check live, and reports what's coming due with an owner next to each.

It watches. It never renews anything, and it never stores the secret itself. Names and dates only.

```
$ shelflife check --inventory inventory.example.yaml --days 60
STATUS    DAYS  EXPIRES     TYPE      NAME                             OWNER                 SOURCE
--------  ----  ----------  --------  -------------------------------  --------------------  ---------
EXPIRING  43    2026-10-27  tls       example.com TLS certificate      platform@example.com  live
OK        123   2027-01-15  api-key   Payment provider live API key    payments@example.com  inventory
OK        198   2027-03-31  license   Issue tracker annual license     it@example.com        inventory
OK        333   2027-08-13  domain    example.com domain registration  it@example.com        live
OK        655   2028-06-30  contract  Office lease                     ops@example.com       inventory

5 items. 1 within 60 days or already expired. 0 could not be checked. Today is 2026-09-14.
$ echo $?
1
```

Real output, run on 2026-09-14. The two `live` rows were checked against example.com just then; the three `inventory` rows are dates somebody typed. The exit code is `1` because something needs attention within the window. `0` means nothing does, `2` means something could not be checked. That is the whole integration story for cron and CI.

## Why this exists

Every team has had the outage. Crates.io went down because an automated renewal failed silently and someone "forgot to check again." GitLab's analytics collector was dark for 22 hours because the certificate was marked defunct in a document and wasn't. A Shopify store owner was locked out for two weeks because their domain expired and their login email was on that domain. The University of Washington's certificate expired the day after Christmas.

And it's getting worse on a schedule. The CA/Browser Forum cut TLS certificate lifetimes from 398 days to 200 in March 2026, to 100 in March 2027, and to 47 in March 2029. Whatever you were tracking by hand, you're about to track it four to eight times as often.

The full reasoning, with sources, is in [engagement/02-discovery.md](engagement/02-discovery.md).

## Running it

You need Python 3.11 or newer and [uv](https://docs.astral.sh/uv/). Install it as a tool, straight from this repository:

```bash
uv tool install git+https://github.com/cruzbuilds/shelflife@v0.1.0
shelflife check --inventory inventory.example.yaml
```

Or run it once without installing anything: `uvx --from git+https://github.com/cruzbuilds/shelflife@v0.1.0 shelflife check -i inventory.example.yaml`. Drop the `@v0.1.0` to track `main` instead of a release. From a clone, `uv sync` then `uv run shelflife ...` does the same thing.

If you're going to change the code, use `uv sync --locked --extra dev` instead. That's what CI installs, and it's what makes `scripts/check.sh` run the same checks locally that gate a pull request. `--locked` means you get exactly the versions in `uv.lock`; if you add a dependency, run `uv lock` and commit the result.

That reads the example inventory, checks the certificate on `example.com` and the registration of `example.com` live, and prints a table: what's expired, what's expiring within 30 days, what's fine, and what couldn't be checked. Change the window with `--days 14`. Get JSON with `--json`. Add `--offline` to skip the live checks and just read the file.

The exit code is the point. `0` means nothing needs attention. `1` means something is expiring or already expired. `2` means something couldn't be checked. Put it in a cron job or a CI step and the non-zero exit is your alert, no parsing needed.

## The inventory

One entry per thing that expires. Copy `inventory.example.yaml` and edit it. Every entry has a name, a type, and an owner, then either:

- a `check` block, for the types the tool can look up live: `tls` (a host and port) and `domain` (a domain name)
- an `expires` date, for everything else: `api-key`, `license`, `contract`, `warranty`, any word you like

The file holds names and dates. It never holds the thing itself. No certificate keys, no API key values, no passwords. That's the whole security model and it's what makes the inventory safe to commit.

JSON works too, same structure, if a script is generating it.

## Reading the report

The `SOURCE` column matters more than it looks. `inventory` means somebody typed that date and nothing has verified it. `live` means the tool checked just now. `unchecked` means it's a live type but the check was skipped (`--offline`). `error` means the check was attempted and failed, and the reason is right there in the row.

## How the live checks work

**`tls`**: the tool connects to the host and port, completes a TLS handshake, reads the expiry date off the certificate the server presents, and disconnects. It sends nothing else. It does not verify the certificate, on purpose: an expired or self-signed certificate is exactly what you want reported, and verification would refuse it before the date could be read. [ADR 0003](docs/decisions/0003-tls-checker-does-not-verify.md) has the reasoning.

**`domain`**: the tool asks [RDAP](https://about.rdap.org/), the registry protocol that replaced WHOIS, when the registration expires. Not every top-level domain has an RDAP server (`.de` is a well-known example). When that happens the report says so and tells you to track that domain with a manual date instead: change its type to something like `domain-manual` and give it an `expires` line.

Both checks time out after ten seconds. A host that does not answer becomes one `error` row and the rest of the report still runs.

## Getting the report somewhere people look

The exit code is the alert for cron and CI. For a chat channel, add a webhook:

```bash
shelflife check --webhook https://hooks.slack.com/services/...
```

or set `SHELFLIFE_WEBHOOK` in the environment and leave the flag off. When the exit code is `1` or `2`, the tool POSTs the same JSON that `--json` prints, with two extra fields, `text` and `content`, holding a one-line summary ("shelflife: 1 expired, 2 expiring within 30 days. Soonest: payments API key (payments@example.com) in 17 days."). Slack renders `text`, Discord renders `content`, and anything else gets the full report to do what it likes with. Nothing is posted when everything is fine, because a daily "all good" is how a channel gets muted. If you want the heartbeat anyway, add `--webhook-always`.

Treat the URL like a password. Anyone who has a Slack incoming webhook URL can post to that channel. That is why it comes from a flag or an environment variable and never from the inventory file, and why it never appears in an error message. It has to start with `https://`; anything else is refused before a byte is sent.

A post that fails prints one `error:` line. If the report had a real deadline in it the exit code stays `1`, because the deadline is still the thing that matters ([ADR 0002](docs/decisions/0002-exit-codes.md)); a failed heartbeat exits `2`.

Unchecked and errored items sort to the top. They're the ones you can't reason about, and burying them under a long list of healthy rows is how they get missed.

## Status

Proof of concept, feature complete against [engagement/03-scope.md](engagement/03-scope.md): the inventory format, validation that refuses anything ambiguous, live checks for TLS certificates and domain registrations, the report, the exit codes, and the webhook. What it has not done yet is run for a month on a real inventory, which is the only test that says whether the alerts are useful or annoying. The "Not production ready" list in the scope document is honest about what that month might find.

## When not to use this

Naming the alternatives is more useful than pretending they don't exist.

- **You already run Prometheus.** Use [ssl_exporter](https://github.com/ribbybibby/ssl_exporter) or [x509-certificate-exporter](https://github.com/enix/x509-certificate-exporter). They are built for that world, ship alert rules and dashboards, and if shelflife ever grows a `--prometheus` flag it will only ever be the basics.
- **You want a dashboard and a status page.** [Uptime Kuma](https://github.com/louislam/uptime-kuma) and [Gatus](https://github.com/TwiN/gatus) both check certificate expiry, Gatus checks domain expiry too, and both give you a UI, notifications to forty services, and a server to keep running. shelflife deliberately has no server.
- **You need one certificate checked once.** `openssl s_client -connect host:443 | openssl x509 -noout -enddate` is right there. shelflife earns its keep when there is a list, the list has owners, and something has to run it every day.
- **You want the tool to renew things.** That is a different tool with a different security story. See the [scope document](engagement/03-scope.md) for why.

What none of those do, and why this exists: one inventory for every kind of expiring thing, not only certificates, with an owner next to each, no server, no stored secrets, and an exit code that any scheduler already understands. The comparison against 51 repositories that informed this section is in [docs/landscape.md](docs/landscape.md).

## Where it could go next

Things people have asked for, in the order I'd do them. None of them are promises.

**A page instead of a terminal.** Most people who would care about this report are not going to run a command to see it. The plan that keeps the tool's shape: `--html report.html` writes one self-contained page with the same rows as the table, and a scheduled GitHub Actions job publishes it, so the report lives at a URL that is always current with no server to run. A dashboard with a backend stays out of scope; the reasons in [engagement/03-scope.md](engagement/03-scope.md) still hold.

**Cloud inventories.** Today the inventory is a file you write. The obvious next step is sources that write it for you: certificates from a cloud provider's certificate service, domains from its DNS service, one source per provider, so a team with more than one cloud gets one report. This is the first feature that would need credentials, read-only ones, and the security story gets written before the code. It is version two, with its own scope document, not a pull request.

**Prometheus output.** `--prometheus` writing the same rows as `days_until_expiry{name=...,type=...,owner=...}` gauges, for teams that scrape everything. One function; the Go tools in this space are all Prometheus-first and it is the lingua franca there.

**Retry, bootstrap, signing.** The smaller items in the handoff's not-production-ready table: one retry on flaky checks, RDAP's bootstrap lookup instead of the redirector, a signature on the webhook payload. Each is a half day and none is needed until someone hits the problem.

If you want one of these, open an issue and say what you'd use it for. That's the input that decides the order.

## What's in here

| Path | What |
| --- | --- |
| `engagement/` | Why this exists, what was found, what's in and out of scope, and (later) how to take it over |
| `docs/decisions/` | Decisions that would be expensive to reverse, recorded as they're made |
| `docs/review-log.md` | Every swarm review, finding by finding, with what got accepted and what a human would have missed |
| `docs/landscape.md` | The 51 repositories this was compared against before going public, and what that changed |
| `scripts/check.sh` | The one command that says whether the repo is healthy. CI runs exactly this. |
| `AGENTS.md` | Working agreement for any AI agent that touches this code |
| `CONTRIBUTING.md` | How to run the checks and what a pull request needs |
| `SECURITY.md` | How to report a problem, and what this tool does and does not trust |
| `CHANGELOG.md` | What changed, by version |
| `.kiro/steering/` | Standards the agents follow |

Built from [project-starter](https://github.com/cruzbuilds/project-starter). Pull requests are reviewed by [agentic-review-swarm](https://github.com/cruzbuilds/agentic-review-swarm) before they merge; what it caught is in [docs/review-log.md](docs/review-log.md).

## License

MIT. See [LICENSE](LICENSE).
