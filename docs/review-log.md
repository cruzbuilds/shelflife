# Review log

Every pull request on this project gets reviewed by the [agentic-swarm](https://github.com/cruzbuilds/agentic-swarm) before a human looks at it. This file records what that review actually produced, PR by PR, so the claim "built with the swarm" comes with numbers instead of vibes.

Each entry answers the same questions. What did the swarm flag? Which of those would a tired human reviewer have missed? What did I override, and why? And what changed in the swarm itself because of this PR? That last one matters most: a review tool that never gets corrected by real use is a review tool nobody trusts.

Scoring rules, so the numbers mean the same thing every time:

- **Blocking / Should fix / Noted** are the swarm's own severities, copied as-is.
- **Accepted** means the fix landed in the same PR. **Deferred** means it became a tracked follow-up. **Overridden** means I disagreed and did not act, with the reason written here.
- **Would have missed** is my honest guess at whether I would have caught it reading the diff myself once, at the end of a long day. It is subjective. It is still the number that decides whether this is worth running.

---

## PR 1: inventory format, validation, report, and CLI

**Reviewed:** 2026-09-14
**Agents that ran:** security-reviewer, docs-reviewer, infra-reviewer, test-reviewer, scope-reviewer (merged by swarm)
**Verdict:** BLOCK
**Wall clock:** about 4 minutes for all five agents plus the merge
**Diff size:** 14 files, roughly 900 lines added

### Findings

| # | Severity | Finding | Agent | Outcome | Would have missed? |
|---|----------|---------|-------|---------|--------------------|
| 1 | Blocking | The YAML loading path had zero tests. Every fixture was JSON, but YAML is the documented default and the only format in the README. | test-reviewer | Accepted: added `tests/fixtures/valid.yaml`, a YAML-vs-JSON identity test, unquoted-date test, `.yml` test, and direct tests of `_parse_date` | Yes. I wrote the JSON fixtures on purpose because PyYAML was not installable in my sandbox, and I had talked myself into "the branch is tiny, it's fine." |
| 2 | Blocking | Exit codes `1` and `2` are a public contract for cron and CI users, but nothing recorded the decision or the precedence rule. Scope only promised "nonzero." | scope-reviewer, docs-reviewer | Accepted: [ADR 0002](decisions/0002-exit-codes.md) | Partly. I knew the codes were a contract, I would not have written the ADR before merging. |
| 3 | Blocking | JSON input shipped as a documented feature but scope said YAML only. The stated reason in a code comment ("so JSON users don't need PyYAML") was not true, since PyYAML is a hard dependency. | scope-reviewer | Accepted: scope doc updated with the change and a re-confirm flag; the misleading comment and its dead branch removed | Yes. This is the one that stings. JSON was there to make my tests easier and I dressed it up as a feature. The reviewer called the rationalization by name. |
| 4 | Should fix | README says `uv sync` but CI runs `uv sync --extra dev`, so following the README gives a weaker local check than the one that gates the PR. | docs-reviewer | Accepted: README paragraph added | Probably. |
| 5 | Should fix | A syntax error in the inventory file produced a raw traceback instead of the `error: ...` line and exit `2` the CLI promises. No test covered it. | test-reviewer | Accepted: parse errors now raise `InventoryError`; tests for malformed JSON, malformed YAML, and empty YAML | Yes. I never fed it a broken file. |
| 6 | Should fix | No `uv.lock` committed and open-ended version bounds, so CI resolves fresh every run and is not reproducible. | infra-reviewer | Deferred: `uv` cannot reach PyPI from where the code was written. Chris runs `uv lock` on his Mac in a follow-up commit and CI switches to `--locked`. | Yes. |
| 7 | Should fix | uv and hatchling chosen with no recorded reason. | scope-reviewer | Accepted: short packaging note at the bottom of ADR 0002 rather than a separate ADR, which the reviewer itself suggested | No, but I would not have written it down either. |
| 8 | Handoff | The "PyYAML is optional" branch was dead code. scope-reviewer noticed it and routed it to a "code-reviewer" that does not exist in the swarm. | scope-reviewer | Accepted: branch removed as part of finding 3 | Maybe. |

**Totals:** 3 blocking, 4 should fix, 1 handoff. 7 accepted, 1 deferred, 0 overridden. Would have missed: 5 of 8.

### Confirmed non-issues

Worth recording because a review that only lists problems trains you to skim it. The swarm checked and cleared: `yaml.safe_load` in use rather than `yaml.load`; CI carries no cloud credentials and already restricts `permissions` to `contents: read`; action pins on version tags accepted because nothing in the workflow touches credentials or deploys; `--inventory` accepting any local path is fine for a local CLI.

### Overrides

None. Every finding was either fixed in this PR or deferred with a named owner.

### What changed in the swarm because of this PR

One defect in the swarm itself. scope-reviewer handed a finding to an agent called "code-reviewer" that is not in the roster, and the swarm merge step correctly caught it under "Handoffs nobody picked up" rather than dropping it. That is the right failure mode, but the root cause is that the shared review contract does not list the actual roster, so an agent guessing at a teammate's name has nothing to check against. Fix tracked in the agentic-swarm repo: the review contract and each charter get the real roster, and the seed suite gets a case that expects a handoff to be routed to a real agent. Logged in that repo's `docs/eval-log.md`.

### What the human did that the swarm did not

Two things. The swarm noted that the scope document's "confirmed with" line was still a blank placeholder. It was right, but that was a process step waiting on Chris, not a code change; he signed it before this PR merged. And the swarm did not question whether the whole PR was too big for one review. Fourteen files is at the edge. Next PR is smaller.

---

## PR 3: live checks for TLS certificates and domain registrations

**Reviewed:** 2026-09-14
**Agents that ran:** security-reviewer, docs-reviewer, infra-reviewer, test-reviewer, scope-reviewer (merged by swarm)
**Verdict:** BLOCK
**Wall clock:** 5 minutes 28 seconds for all five agents plus the merge
**Diff size:** 13 files, roughly 700 lines added

(PR 2 was the lock file, one commit, no swarm review. It was itself a swarm finding from PR 1.)

### Findings

| # | Severity | Finding | Agent | Outcome | Would have missed? |
|---|----------|---------|-------|---------|--------------------|
| 1 | Blocking | The TLS checker's timeout branch had no test, and it is the one failure mode the README promises to handle. | test-reviewer | Accepted: injected `TimeoutError` test | Yes. |
| 2 | Blocking | The RDAP checker's network-failure and timeout branches were untested; every test fed it a canned response, none made the fetch raise. | test-reviewer | Accepted: two injected-exception tests | Yes. |
| 3 | Blocking | Valid JSON of the wrong shape (an array) hit an untested guard. | test-reviewer | Accepted | Probably. |
| 4 | Blocking | The DER parser's length-field validation was untested. The reviewer's point: this PR is what makes that parser reachable from an unverified network peer, so its defensive branches are the most important lines in the diff to prove. | test-reviewer | Accepted: bad-length, indefinite-length tests | Yes, and this is the best finding of the review. I tested the happy path with real certificates and the obvious junk, and skipped the branch that matters for hostile input. |
| 5 | Blocking | Two error branches in the time parser untested. | test-reviewer | Accepted, plus a direct test of both time encodings | Probably. |
| 6 | Should fix | The RDAP response body was read with no size cap. A misbehaving server could exhaust memory on the machine running the cron job. | security-reviewer | Accepted: 1 MB cap, refused with a message past that | Yes. |
| 7 | Should fix | Depending on `rdap.org`, a third-party redirector, is a boundary decision of the same weight as the no-verify choice that got ADR 0003, and it only had a docstring. | docs-reviewer | Accepted: ADR 0004 | Yes. I had made the decision carefully and not written it down, which is the exact failure ADR 0001 exists to stop. |
| 8 | Should fix | `--offline` is new user-facing surface not in the scope document. | scope-reviewer | Accepted: one line in scope, dated | No, but I would have skipped it. |
| 9 | Should fix | `test_unresolvable_host` did a real DNS lookup, against the scope rule that checker tests never touch the network. | test-reviewer | Accepted: injected `gaierror` | No. I knew and let it slide. The reviewer did not. |
| 10 | Handoff | Does the CI runner have `openssl`? If not, the real-handshake tests skip silently and coverage drops with no signal. | test-reviewer, docs-reviewer | Accepted: the tests now fail in CI (`CI=true`) when `openssl` is missing, and still skip locally | Yes. |
| 11 | Handoff | No review-log entry for this PR yet. | test-reviewer | No change needed: the entry is written after the review, which is this. | n/a |

**Totals:** 5 blocking, 4 should fix, 2 handoffs. 10 accepted, 0 deferred, 0 overridden, 1 no change needed. Would have missed: 6 of 10.

### Confirmed non-issues

security-reviewer reviewed the DER parser specifically as attacker-reachable input and found every read bounds-checked. security-reviewer and scope-reviewer both independently checked `CERT_NONE` against ADR 0003 and accepted it. docs-reviewer confirmed README, ADR 0003, and the checker code agree on timeouts, flags, fallback behavior, and exit codes.

### Overrides

None.

### What changed in the swarm because of this PR

Nothing in the charters. The roster fix from PR 1 held: scope-reviewer and test-reviewer both handed findings to real agents this time, and the merge step listed the two that nobody confirmed under "Handoffs nobody picked up" with the right names.

One thing in how the swarm was run. test-reviewer reported it could not execute the test suite because the harness did not grant it shell approval, and scope-reviewer reconstructed the diff from `.git/logs/HEAD` because it had no git access. Both said so plainly under Noted instead of pretending, which is what the contract asks. But a test reviewer that cannot run tests is reviewing with one eye shut. Next run gets an explicit tool allowlist so the agents can run `git`, `python`, and `uv`. That is a runner concern, tracked in the agentic-swarm repo.

### Second pass, after the fixes

The fixed branch went back through the swarm, this time via `scripts/review.sh` with a tool allowlist. Verdict: BLOCK again, and this pass is the more interesting one.

| # | Severity | Finding | Agent | Outcome | Would have missed? |
|---|----------|---------|-------|---------|--------------------|
| 12 | Blocking | The RDAP fetch followed redirects with no check on where they go. security-reviewer proved it experimentally: a `302` to `http://127.0.0.1:<port>/` was followed. Since the first hop is a third-party redirector by design (ADR 0004), a bad redirect turns the tool into a way to make requests at internal addresses from wherever the cron job runs, cloud metadata endpoints included. | security-reviewer | Accepted: redirects are now followed only to HTTPS hosts whose addresses are all public; IP literals are checked without resolving; tests drive the real fetch against a local server that redirects to loopback, to `169.254.169.254`, and to plain HTTP, and all three are refused before any request goes out | Yes. This is the finding of the day. I wrote ADR 0004 about the redirector being *down* and never thought about it being *wrong*. |
| 13 | Blocking | The real `fetch_url`, including the 1 MB cap added in the first pass, had no test at all. Every RDAP test injected a stand-in fetch. The cap could regress and nothing would fail. | test-reviewer | Accepted: `tests/test_rdap_http.py` runs a local HTTP server and drives the real function through headers, error bodies, and an oversized body | Yes. I fixed the cap and tested the parser, not the cap. |
| 14 | Blocking | `uv sync --locked` with no `uv.lock` in the repo. | infra-reviewer, test-reviewer | No change needed: an artifact of the review environment. The copy the swarm reviewed was taken from a sandbox that could not fetch PR 2 (the lock file), so from where it stood the finding was true and it reproduced it by running the command. On GitHub and on the machine the branch was built on, the lock file is there. Recorded because a reviewer that reproduces its finding is doing the right thing even when the environment is lying to it. | n/a |
| 15 | Should fix | README said CI installs with `uv sync --extra dev`; it now uses `--locked`. | docs-reviewer | Accepted | No. |
| 16 | Should fix | Fixture README said the openssl tests skip when it's missing, which is only true locally; in CI they fail. | docs-reviewer | Accepted | Probably. |
| 17 | Should fix | `--offline` was added to scope with a note but not the pending-reconfirmation flag the JSON change got. | scope-reviewer | Accepted: folded into the same pending line | No. |
| 18 | Should fix | `fetch_certificate`'s "handshake but no certificate" guard was untested through the function itself. | test-reviewer | Accepted: the handshake is behind a seam and the guard has a direct test | Probably. |
| 19 | Should fix | Nothing in CI states or checks that `openssl` is on the runner. | infra-reviewer | Accepted: one `openssl version` step | No, but cheap. |

**Second pass totals:** 3 blocking, 5 should fix. 7 accepted, 1 no change needed, 0 overridden. Would have missed: 4 of 7.

**Both passes, this PR:** 8 blocking, 9 should fix, 2 handoffs. 17 accepted, 2 no change needed, 0 overridden. Would have missed: 10 of 17. 91 tests at the end, up from 67 when the PR was first reviewed.

The swarm also wrote, under "Noticed while merging," that the review log entry in the diff claimed everything had been found and fixed, that every agent was told not to trust that narrative, and that they verified it independently. That paragraph is the best argument for running a second pass I have seen: the log said "done," and the swarm treated "done" as a claim to check.

### What the human did that the swarm did not

Chose the approach. The swarm cannot tell you that Python's `ssl` module refuses to hand back an expired certificate, or that the fix is forty lines of DER walking instead of a dependency. It can only tell you whether the forty lines are tested. It did, twice, and the second time it found the hole the first time made possible.

---

## PR 4: rename to shelflife, webhook alert, and the handoff document

**Reviewed:** 2026-09-14
**Agents that ran:** security-reviewer, docs-reviewer, infra-reviewer, test-reviewer, scope-reviewer (merged by swarm), via `scripts/review.sh`
**Verdict:** BLOCK
**Wall clock:** 6 minutes 16 seconds
**Diff size:** 8 files, roughly 500 lines added

The rename commit is mechanical and rode along in the same pull request; the swarm reviewed the webhook diff on its own.

### Findings

| # | Severity | Finding | Agent | Outcome | Would have missed? |
|---|----------|---------|-------|---------|--------------------|
| 1 | Blocking | A webhook URL with a typo (no `https://`, or empty) made `urllib` raise a bare `ValueError` that nothing caught. The process crashed with a traceback containing the full URL, which the module docstring had just promised never happens, and the exit code was neither 0, 1, nor 2. Both agents reproduced it. | security-reviewer, test-reviewer | Accepted: the URL is validated before anything is sent (HTTPS only, host required, empty refused); any other exception in the post becomes a `WebhookError` naming the exception type and nothing else; tests for each | Yes. I tested every failure I could think of and not the one a person actually makes, a typo. |
| 2 | Should fix | The shared redirect rule only guards redirects; the webhook's initial URL was unchecked, so `file:///etc/passwd` opened successfully (with a `None` status that then crashed the status check). | security-reviewer | Accepted: same fix as 1, plus a non-integer status is now a clean failure; `net.py`'s docstring no longer claims "one rule, applied everywhere" and says who checks the first request | Yes. |
| 3 | Should fix | Exit-code precedence when the webhook fails on a run that was already 2 was correct but unpinned by a test. | test-reviewer | Accepted | No. |
| 4 | Should fix | Flag-over-environment precedence for the URL was untested. | test-reviewer | Accepted | Probably. |
| 5 | Handoff | README now says "feature complete against scope" while `04-handoff.md` was still the blank template. | scope-reviewer | Accepted: the handoff was being written while the review ran; it's in this PR | No. |
| 6 | Noted | DNS rebinding: a redirect target is resolved once for the check and again for the connection. Pre-existing, not a regression. | security-reviewer | Recorded in the handoff's not-production-ready table and in `net.py`, with what it would take to close | Yes. |

**Totals:** 1 blocking, 3 should fix, 1 handoff, 1 noted. All accepted, 0 overridden. Would have missed: 3 of 5.

### Confirmed non-issues

The swarm confirmed the `net.py` extraction preserved the redirect logic verbatim with tests intact; that the webhook is in scope and needs no new ADR; that keeping the URL out of the inventory upholds the existing rule; and that the README's webhook section matches the code. test-reviewer ran the suite (107 at review time, 114 after fixes).

### What the human did that the swarm did not

Decided that a failed post on a run with a real deadline keeps exit `1`. The swarm confirmed it matched ADR 0002 and moved on. Whether that's the right call is an open question in the handoff, and the answer will come from a month of cron, not from a reviewer.

### Running total, four pull requests

30 findings from four swarm passes: 12 blocking, 16 should fix, 2 handoffs. 27 accepted, 1 deferred then done, 2 no change needed, 0 overridden. Author's count of would-have-missed: 18 of 30.

---

## PR 5: what a public repository is expected to have

**Reviewed:** 2026-09-14
**Agents that ran:** all five, via `scripts/review.sh`
**Verdict:** BLOCK
**Wall clock:** 4 minutes 44 seconds
**Diff size:** 7 files, documentation and metadata only, no code

Included here because a docs-only diff got blocked for two real reasons, and because it is the first review where test-reviewer returned a clean PASS on the grounds that nothing testable changed, which the merge report called "a real PASS, not a shrug."

### Findings

| # | Severity | Finding | Agent | Outcome | Would have missed? |
|---|----------|---------|-------|---------|--------------------|
| 1 | Blocking | README, CONTRIBUTING, and SECURITY all describe a `uv sync --locked` workflow and there was no `uv.lock` in the copy reviewed. | docs-reviewer | No change needed: the sandbox copy again. Fixed at the source this time by copying the real lock file into the review environment so this stops recurring. | n/a |
| 2 | Blocking | CHANGELOG and README say "feature complete against scope" while the scope document itself still carries a "pending re-confirmation" flag for JSON input and `--offline`, with the confirmed-with date untouched. The release was making a claim the scope document contradicted. | scope-reviewer | Accepted: Chris re-confirmed both in writing, the scope date is signed, and the changelog says so instead of "feature complete." | Yes. I wrote "feature complete" three times without rereading the document that defines it. |
| 3 | Should fix | The install one-liner pulled from an unpinned `git+` URL, so it installed whatever `main` was, not the `v0.1.0` the same README documents, and no tag existed. | security-reviewer, infra-reviewer | Accepted: install lines pin `@v0.1.0`, with "drop it to track main" spelled out; the tag is cut with the release. | Probably. |
| 4 | Should fix | `docs/landscape.md` said 21 repositories in the table; the table had 19. | docs-reviewer | Accepted: two archived projects are named as excluded. | Yes. I counted what I read, not what I listed. |
| 5 | Should fix | `--prometheus` described as "(planned)" in one section and hedged with "none of these are promises" in another. | scope-reviewer | Accepted: same hedge in both places. | No. |
| 6 | Handoff | The review copy's git remote still pointed at the old repository name. | security-reviewer | No change needed: the sandbox copy; GitHub was renamed hours earlier. | n/a |
| 7 | Noted | SECURITY.md claimed Dependabot watches dependencies and there was no `dependabot.yml`. | docs-reviewer | Accepted: alerts were on in repository settings; the file now exists too, so the claim is true on disk as well. | Probably. |

**Totals:** 2 blocking, 3 should fix, 1 handoff, 1 noted. 5 accepted, 2 no change needed, 0 overridden. Would have missed: 3 of 5.

### What the swarm did that surprised me

docs-reviewer checked the terminal output in the README against `inventory.example.yaml` and the date math by hand, and reported it "internally consistent." Then it noted that whether the block is "genuinely real output" is a claim no test can verify. It is real (see the screenshot in the pull request), but the reviewer was right that the README asserts something it cannot prove, and right not to pretend otherwise.

### Caught between reviews, worth recording

The GitHub account was renamed from `Cruzcodez` to `cruzbuilds` after these five pull requests merged. Every link in the repository still named the old account. They redirected, so nothing looked broken, and no agent had flagged them because the links were correct when they were written.

This is the failure mode the swarm cannot catch: not a defect in a diff, but a fact about the world changing underneath a diff that was right at the time. The fix and the reasoning are in [ADR 0005](decisions/0005-username-rename.md). The part that made it urgent rather than cosmetic is that two of the stale links were install commands, and a retired GitHub username can be claimed by anyone.

### Running total, five pull requests

37 findings from five swarm passes: 14 blocking, 19 should fix, 3 handoffs, 1 noted. 32 accepted, 1 deferred then done, 4 no change needed, 0 overridden. Author's count of would-have-missed: 21 of 33 actionable.
