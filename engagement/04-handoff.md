# 4. Handoff

**Date:** 2026-09-14
**Built by:** Chris Cruz, with Claude doing the typing and the [agentic-review-swarm](https://github.com/cruzbuilds/agentic-review-swarm) reviewing every pull request
**Handed to:** whoever runs it next. Most likely Chris in a few months, with no memory of any of this.

Write this at the end, for the person who gets this after you. That might be a customer, a teammate, or you in eight months with no memory of any of it.

Assume they know their own job but nothing about this project. Explain the parts that are specific to what you built. Don't explain what a Lambda function is, do explain why there are two of them.

---

## What this is

> A command-line tool that keeps one inventory of everything you have that expires (TLS certificates, domain registrations, API keys, licenses, contracts), checks the ones it can check live, and reports what's coming due with an owner next to each item. The exit code is the alert: `0` fine, `1` something is expiring or expired, `2` something could not be checked. Optionally it posts the report to a webhook. The question it answers: "what's going to take us down next month that nobody is watching?"

## What it doesn't do

Straight from the out-of-scope list in `03-scope.md`. Repeat it here, because this is the document people actually keep.

- It never renews or rotates anything. It watches. The moment it acts, it needs credentials to everything it watches, and that's a different project.
- It never stores secret values. Certificate keys, API key values, passwords: the inventory holds names and dates only. This is a rule, not a missing feature.
- No web interface. The report is the interface; `--json` feeds anything that wants a page.
- No native Slack, email, or PagerDuty integrations. The webhook covers them.
- No cloud provider integrations (pulling certs from ACM, domains from Route 53). Deliberately: the core is cloud-free.
- No multi-user, auth, or roles. One inventory file, one team, trust the filesystem.
- No dependency tracking between items (this domain expiring breaks that login).
- Not tested on Windows.

## This is not production ready

Read this part before you deploy anything.

| What's missing | Why it matters | Roughly what it takes |
| --- | --- | --- |
| A scheduler | It runs when something runs it. Nothing inside it repeats. | A cron line or a CI job. Ten minutes. The README shows the cron form. |
| Retry or backoff on live checks | A flaky connection reads as a failed check and exits `2`. Once a day that's tolerable; on a busy network it's noise. | One retry with a short wait in `checkers/tls.py` and `checkers/rdap.py`, behind the same `fetch` seam the tests use. An hour, plus a test per checker. |
| A fallback when rdap.org is down | Every `domain` item errors at once. [ADR 0004](../docs/decisions/0004-rdap-via-redirector.md) accepted this for a proof of concept. | Implement IANA's RDAP bootstrap lookup behind the existing `fetch` seam. About a hundred lines and a cache. Half a day. |
| Webhook authentication | The webhook posts with no signature. Fine for a Slack incoming webhook, which is secret by URL. Not fine for a receiver that trusts the payload. | An HMAC header over the body, and a documented way for receivers to verify it. Half a day. |
| DNS rebinding on redirects | A redirect target is resolved once to check its addresses are public, then again by the connection. A name that answers public the first time and private the second would get through. Needs a hostile DNS server pointed at by a hostile registry or webhook receiver, so unlikely, but real. | Connect to the checked address directly and set SNI by hand in `net.py`. A day, and it makes the HTTP code noticeably harder to read. |
| A month of real use | Nobody has run it against a real inventory long enough to know whether the alerts are useful or annoying, whether the 30-day default is right, or which TLDs fall back to manual dates in practice. | Run it. Adjust `--days`. Write down what was wrong. |
| Certificates from many real CAs | The certificate parser has been tested against openssl-generated certificates and junk input, not against the variety real CAs produce. A certificate it cannot read becomes an `error` row, never a wrong date. | Point it at fifty real hosts and see. An afternoon. If one fails, the fix is either a small parser change or swapping in the `cryptography` package ([ADR 0003](../docs/decisions/0003-tls-checker-does-not-verify.md) says when). |

The common things to check are covered or not applicable: input validation (the inventory loader refuses anything ambiguous, and every byte from the network is bounds-checked), error handling (every failure is a report row or an `error:` line, never a traceback), secrets (there are none in the tool; the webhook URL is the one credential and it stays out of the inventory), logging (stdout is the report, stderr is errors, nothing else), rate limiting and traffic (it is a CLI that runs once; there is no server).

## Running it

Exact commands. Assume they're starting from a fresh machine and a fresh clone.

```bash
# prerequisites: Python 3.11 or newer, and uv (https://docs.astral.sh/uv/)
git clone https://github.com/cruzbuilds/shelflife
cd shelflife

# install
uv sync

# configure: copy the example inventory and edit it
cp inventory.example.yaml inventory.yaml
#   every item: name, type, owner, and either a check block (tls, domain) or an expires date

# run
uv run shelflife check --inventory inventory.yaml
uv run shelflife check --inventory inventory.yaml --days 14 --json
uv run shelflife check --inventory inventory.yaml --webhook https://hooks.slack.com/services/...

# as a cron job: the non-zero exit is the alert
# 0 8 * * *  cd /path/to/shelflife && uv run shelflife check -i inventory.yaml || mail -s "shelflife" ops@example.com

# checks (what CI runs)
uv sync --locked --extra dev && ./scripts/check.sh
```

### Things it needs to exist

- Outbound network to whatever hosts the `tls` items name (port 443 or whatever port they specify), and HTTPS to `rdap.org` and the registry it redirects to for `domain` items. Without it, use `--offline`: manual-date items still report, live items show as `unchecked`, exit code is `2`.
- `openssl` on the PATH, but only to run the test suite (it generates a throwaway certificate). The tool itself does not need it.
- A webhook URL, only if you want the report posted somewhere. Slack: create an incoming webhook for the channel. Discord: channel settings, integrations, webhooks. Put the URL in `SHELFLIFE_WEBHOOK` or pass `--webhook`.
- Nothing else. No accounts, no credentials, no cloud.

## How it's put together

> One inventory file goes in. `inventory.py` reads and validates it into `Item` objects and refuses anything ambiguous (no owner, a live type with a typed date, a manual type with no date). `report.py` turns Items into Results: manual items carry their date from the file, live items get handed to a checker from `checkers/` (`tls.py` does a real handshake and reads the date off the certificate with the small parser in `x509.py`; `rdap.py` asks RDAP). Any checker failure becomes a Result with `source: error` and the run continues. `report.py` then renders a table or JSON and computes the exit code. `cli.py` is argparse around all of that, and `webhook.py` POSTs the JSON report when asked. `net.py` holds the one network rule everything shares: a redirect is followed only to a public HTTPS host.

### Where to change things

| If you want to change... | Look in... |
| --- | --- |
| What a valid inventory item is | `src/shelflife/inventory.py`, and the tests in `tests/test_inventory.py` say what is currently refused and why |
| Add a new live type (say, `ssh-host-key`) | Add `LIVE_TYPES` in `models.py`, a required-keys entry in `inventory.py`, a checker in `checkers/`, register it in `checkers/__init__.py`, and tests that use recorded responses, never the network |
| What the report looks like | `render_table` and `render_json` in `src/shelflife/report.py` |
| The exit code rules | Don't, without a new ADR superseding [0002](../docs/decisions/0002-exit-codes.md). Cron jobs depend on them. |
| The webhook payload | `build_payload` and `summary_line` in `src/shelflife/webhook.py` |
| Timeouts | `DEFAULT_TIMEOUT` at the top of each checker and of `webhook.py` |

## Tearing it down

**Don't skip this.**

There is nothing to tear down. The tool creates no cloud resources, no accounts, and no files other than what you point it at.

```bash
# teardown
rm -rf shelflife          # the clone
crontab -e                # remove the line, if you added one
```

### Manual cleanup

- [ ] The cron entry or CI job, if you set one up
- [ ] The Slack or Discord webhook, if you created one for this. Delete it in that tool's settings; the URL is a credential and it stays live after you stop using it
- [ ] `SHELFLIFE_WEBHOOK` from wherever you set it

Nothing else. No IAM, no storage, no DNS, no certificates, no third-party API keys.

## What we learned

> The thing that made this tractable was refusing to store the secret itself. Every "track our certificates" tool eventually asks for access to the certificates, and then it's a security project. Names and dates only means the inventory is safe to commit and the tool needs no credentials, and both of those fell out of one sentence in scope.
>
> Python's `ssl` module will not hand you a parsed certificate it could not verify, and an expired certificate is exactly the one you want to read. That cost a small DER parser (`x509.py`), forty lines that read one field. Worth it over a dependency for a tool whose whole pitch is "no fancy tech," but it is the one piece of the code a maintainer should read carefully before touching.
>
> Reviewing every pull request with the swarm before opening it changed what got built. The review log (`docs/review-log.md`) has the per-finding scorecard, but the short version: three real pull requests, 25 findings, none overridden, and by the author's count 15 would have been missed reading the diff alone. The best one was a redirect hole in the RDAP checker that a reviewer found by standing up a server and proving the tool would follow a redirect to `127.0.0.1`. That was an hour-old piece of code its author felt fine about.
>
> Two things went sideways. JSON input shipped in the first pull request because it made tests easier, dressed up as a feature; the scope reviewer named it. And the first version of every network path was tested only through injected stand-ins, so the real HTTP code had no coverage until a second review pass said so. The pattern both times: the thing that made testing convenient was the thing not being tested.

## Open questions

- Is 30 days the right default window? For certificates on the new 47-day lifetimes it might be too long; for a contract with a 90-day notice period it's too short. The `--days` flag exists, but the default is what most people will run.
- Which TLDs actually fall back to manual dates in practice? `.de` is known. The list will grow with use and should be written down in the README when it does.
- Should a failed webhook post change the exit code when the report had a deadline in it? Right now it doesn't (ADR 0002: `1` outranks `2`). Reasonable people could disagree.
- Is the JSON input format worth keeping? It's in scope as a pending change. If nothing ever generates JSON inventories, remove it.

## Who to ask

> Chris Cruz, github.com/cruzbuilds. The engagement folder and the decisions folder are the memory; read those before asking.

---

## Prompt for your AI assistant

This one reviews your handoff by trying to use it, which is a different job from writing it.

```
Here's a handoff document for a proof of concept:

[paste 04-handoff.md]

And here's the repository structure:

[paste output of: find . -type f -not -path './.git/*' | sort]

Read it as someone who has just inherited this project, knows their way
around software generally, and knows nothing about this specific thing.

Tell me:
- Where would I get stuck trying to run this from scratch? Name the exact step.
- What does it assume I already know that it didn't explain?
- What's in the repo that the handoff never mentions?
- Is the teardown section actually complete, given what's in the repo? What
  would still be running and costing money if I followed it exactly?
- Does "not production ready" say specific things, or is it hand-waving?

Don't be polite about it. A handoff that reads fine and leaves someone stuck
is worse than no handoff, because they'll waste a day before asking.
```
