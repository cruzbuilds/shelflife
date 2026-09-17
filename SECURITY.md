# Security

## Reporting a problem

Open a [GitHub security advisory](https://github.com/cruzbuilds/shelflife/security/advisories/new) on this repository. That keeps the report private until there is a fix. Please do not open a public issue for something exploitable.

You will get an acknowledgement within a few days. This is one person's project, so "within a few days" is the honest number.

## What this tool trusts, and what it does not

**The inventory file is trusted.** It comes from the person running the tool. A hostile inventory can point the TLS checker at any host and port, which is the same thing the operator could do with `openssl`. It cannot make the tool store or send anything it would not otherwise.

**Every byte from the network is untrusted.** The TLS checker reads a certificate from a server it does not verify, on purpose ([ADR 0003](docs/decisions/0003-tls-checker-does-not-verify.md)), so the certificate parser in `src/shelflife/x509.py` treats its input as hostile: every length is bounds-checked, anything it does not understand is refused, and it reads one field. The RDAP checker caps response bodies at 1 MB and parses them with the standard JSON library.

**Redirects are followed only to public HTTPS hosts.** The RDAP lookup goes through a third-party redirector by design ([ADR 0004](docs/decisions/0004-rdap-via-redirector.md)), and the webhook posts to a URL the operator typed. In both cases a redirect could point at an internal address. `src/shelflife/net.py` refuses any redirect that is not HTTPS or whose host resolves to a non-public address, before a request is made. Known limit: the host is resolved once for the check and again for the connection, so a DNS rebinding attack could get through. This is recorded in the handoff document with what it would take to close.

**The webhook URL is a credential.** It comes from a flag or an environment variable, never from the inventory, must start with `https://`, and never appears in an error message or a traceback.

**Nothing is stored.** The tool writes no files unless asked (`--json` to stdout, `--html` when it exists). It holds no keys, tokens, or passwords, and the inventory format has no field for them.

## Dependencies

One runtime dependency, PyYAML, loaded with `safe_load`. Everything else is the Python standard library. Versions are pinned in `uv.lock`; Dependabot alerts are enabled on the repository and `.github/dependabot.yml` asks for update pull requests weekly.
