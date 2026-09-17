# Contributing

Thanks for looking. This is a small tool with a narrow job, and the best contributions keep it that way.

## Before you write code

Read [engagement/03-scope.md](engagement/03-scope.md). It says what this tool does, what it deliberately does not do, and how scope changes. A pull request that adds something from the out-of-scope list will be closed with a pointer to that document, not because the idea is bad but because it was already considered.

If you want to change how something works rather than fix it, open an issue first and say what you would use the change for. That is the input that decides the order of the "Where it could go next" list in the README.

## Running the checks

You need Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked --extra dev
./scripts/check.sh
```

That is exactly what CI runs. It scans for credential-shaped files, lints and format-checks with ruff, and runs the tests with pytest. If it passes locally it passes in CI; if you find a case where that is not true, that is a bug worth reporting on its own.

The TLS tests generate a throwaway certificate with `openssl` and run a real handshake against a local server. If `openssl` is not on your PATH those tests skip locally and say so. Nothing in the suite touches the network.

`uv run pre-commit install` sets up the same ruff checks to run before every commit.

## What a pull request needs

The template asks for four things and means them: what changed, why, how a reviewer can verify it without trusting you, and what could break. Then the checklist:

- `./scripts/check.sh` passes
- New behavior has a test that fails without the change. A test that cannot fail is decoration.
- No secrets, live endpoints, or resource identifiers. The inventory format holds names and dates only, and so does the repository.
- README updated if behavior, setup, or limitations changed
- An ADR in `docs/decisions/` if the change constrains future work. The exit codes, the no-verify TLS check, and the RDAP redirector each have one; read them to see the bar.

## How reviews work here

Every pull request goes through the [agentic-review-swarm](https://github.com/cruzbuilds/agentic-review-swarm) before a person reads it, and the findings are recorded in [docs/review-log.md](docs/review-log.md) with an honest column for whether the author would have caught them alone. Expect a BLOCK on the first pass; it has happened to every pull request so far, including the author's. That is the review doing its job, not a judgment.

## Style

Plain language in docs and comments. Say what something does and why, not how clever it is. Error messages say what went wrong and what to do about it. Small is the default: a fix that solves the problem in 20 lines beats one that solves it in 200 with room to grow.
