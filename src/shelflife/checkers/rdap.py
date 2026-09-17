"""Domain checker: ask RDAP when the registration expires.

RDAP is the JSON protocol that replaced WHOIS for registration data (RFC 9083). Registries run
their own servers; https://rdap.org is a public redirector that sends a domain lookup to the
right one, so this checker does not need to know which registry owns which TLD.

Not every TLD has an RDAP server. The redirector answers 404 with a JSON body that says so, and
the checker turns that into a readable error. The scope document says such domains fall back
to a manual date, which in practice means: change the item's type from `domain` to something
manual and enter the date by hand. The report will say "inventory" for that item's source.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date, datetime

from ..models import Item
from ..net import safe_opener

RDAP_BASE = "https://rdap.org/domain/"
DEFAULT_TIMEOUT = 10.0
# A domain object is a few kilobytes. Anything past this is not an answer we want to parse.
MAX_BODY_BYTES = 1_000_000
USER_AGENT = "shelflife (+https://github.com/cruzbuilds/shelflife)"

# Seam for tests: something that takes a URL and returns (status, body text).
FetchJson = Callable[[str, float], tuple[int, str]]


def fetch_url(url: str, timeout: float = DEFAULT_TIMEOUT) -> tuple[int, str]:
    """GET a URL and return (status, body). Redirects are followed only to public HTTPS hosts."""
    request = urllib.request.Request(
        url, headers={"Accept": "application/rdap+json", "User-Agent": USER_AGENT}
    )
    opener = safe_opener()
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310
            return response.status, _read_capped(response)
    except urllib.error.HTTPError as e:
        return e.code, _read_capped(e)


def _read_capped(response) -> str:
    body = response.read(MAX_BODY_BYTES + 1)
    if len(body) > MAX_BODY_BYTES:
        raise RuntimeError(
            f"RDAP response larger than {MAX_BODY_BYTES} bytes; refusing to parse it"
        )
    return body.decode("utf-8", errors="replace")


def rdap_expiry(item: Item, fetch: FetchJson = fetch_url) -> date:
    """Checker for `type: domain` items. `item.check` carries the domain, validated by inventory."""
    domain = item.check["domain"].strip().lower().rstrip(".")
    try:
        status, body = fetch(RDAP_BASE + domain, DEFAULT_TIMEOUT)
    except urllib.error.URLError as e:
        raise RuntimeError(f"RDAP lookup for {domain} failed: {e.reason}") from e
    except TimeoutError as e:
        raise RuntimeError(
            f"RDAP lookup for {domain} did not answer within {DEFAULT_TIMEOUT:g}s"
        ) from e

    if status == 404:
        raise RuntimeError(_explain_404(domain, body))
    if status != 200:
        raise RuntimeError(f"RDAP lookup for {domain} returned HTTP {status}")

    try:
        payload = json.loads(body)
    except ValueError as e:
        raise RuntimeError(f"RDAP response for {domain} was not JSON") from e

    return expiration_from(payload, domain)


def expiration_from(payload: object, domain: str) -> date:
    """Pull the expiration event out of an RDAP domain object."""
    if not isinstance(payload, dict):
        raise RuntimeError(f"RDAP response for {domain} was not a domain object")
    for event in payload.get("events") or []:
        if isinstance(event, dict) and event.get("eventAction") == "expiration":
            when = str(event.get("eventDate", ""))
            try:
                return datetime.fromisoformat(when.replace("Z", "+00:00")).date()
            except ValueError as e:
                raise RuntimeError(
                    f"RDAP gave an unreadable expiration date for {domain}: {when!r}"
                ) from e
    raise RuntimeError(f"RDAP has no expiration event for {domain}; enter the date by hand")


def _explain_404(domain: str, body: str) -> str:
    # rdap.org says "No RDAP service is available for this resource" when the TLD has no server.
    # A registry that has a server but no such domain answers 404 with an empty or unrelated body.
    try:
        title = json.loads(body).get("title", "")
    except (ValueError, AttributeError):
        title = ""
    if "No RDAP service" in title:
        tld = domain.rsplit(".", 1)[-1]
        return f".{tld} has no RDAP service; track {domain} with a manual date instead"
    return f"{domain} is not registered, or the registry does not publish it over RDAP"
