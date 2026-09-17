# 5. The GitHub account is cruzbuilds, and old links are a liability

**Status:** Accepted
**Date:** 2026-09-17

## Context

This repository was published under the GitHub account `Cruzcodez`. The account was renamed to `cruzbuilds`. GitHub redirects the old URLs, so nothing broke the day of the rename, and it is tempting to leave the old links alone.

That is a trap. GitHub releases a retired username back into the pool, and anyone may register it. The redirect from `Cruzcodez/shelflife` survives only until someone claims `Cruzcodez` and creates a repository by that name. At that moment every stale link in this repository points at a stranger's code, and two of those links are install commands:

```
uv tool install git+https://github.com/Cruzcodez/shelflife@v0.1.0
uvx --from git+https://github.com/Cruzcodez/shelflife@v0.1.0 shelflife check
```

A reader who copies one of those is not fetching a broken URL. They are fetching whatever the new owner put there, and running it. The same applies to the sibling project's plugin install line, which a user pastes into an agent that then reads those files as instructions.

## Decision

No URL in this repository names a GitHub account other than the current one. Every reference to `Cruzcodez` is replaced with `cruzbuilds`, including:

- install commands and clone URLs
- badge image and link URLs
- `pyproject.toml` project URLs
- the security advisory link in `SECURITY.md`
- the `User-Agent` strings the TLS and RDAP checkers send, since a registry operator reading their logs should be able to find the real project

A rename is not finished when the redirect works. It is finished when nothing depends on the redirect.

## Consequences

- Links in this repository survive someone else claiming the old username.
- Links that live outside this repository do not, and cannot be fixed from here: the v0.1.0 release notes, any comment already posted, and anything a reader has already bookmarked. This is unavoidable and worth knowing.
- Old commit trailers keep the previous noreply address. The numeric prefix is the account ID, which does not change on rename, so attribution still resolves. New commits use the current address.
- If this account is ever renamed again, this document is the checklist: grep the repository for the old name and expect to find install commands among the hits.
