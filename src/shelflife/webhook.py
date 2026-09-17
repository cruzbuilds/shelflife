"""Send the report somewhere people already look.

One generic HTTP POST with a JSON body. That's it. Slack incoming webhooks, Discord webhooks,
Teams connectors, and most email gateways all accept one, so this covers them without a
per-vendor integration (which scope rules out, and for good reason: each one is maintenance
forever).

The payload is the same document `--json` prints, plus two fields that make it render as a
readable message where that matters: `text` (Slack reads this) and `content` (Discord reads
this). Both hold the same one-line summary. Receivers that don't know those fields ignore them.

The URL is a credential: anyone who has a Slack incoming webhook URL can post to that channel.
So it comes from a flag or the SHELFLIFE_WEBHOOK environment variable, never from the inventory
file, and it never appears in an error message.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date

from .models import Result
from .net import RedirectError, safe_opener
from .report import render_json, sort_for_report

DEFAULT_TIMEOUT = 10.0
USER_AGENT = "shelflife (+https://github.com/cruzbuilds/shelflife)"

# Seam for tests: something that POSTs a JSON body and returns the HTTP status.
Poster = Callable[[str, bytes, float], int]


class WebhookError(RuntimeError):
    """The post did not land. The message never includes the URL."""


def summary_line(results: list[Result], today: date, threshold_days: int) -> str:
    """One sentence a person can read in a notification without opening anything."""
    counts: dict[str, int] = {}
    for r in results:
        s = r.status(today, threshold_days)
        counts[s] = counts.get(s, 0) + 1
    parts = []
    if counts.get("expired"):
        parts.append(f"{counts['expired']} expired")
    if counts.get("expiring"):
        parts.append(f"{counts['expiring']} expiring within {threshold_days} days")
    trouble = counts.get("error", 0) + counts.get("unchecked", 0)
    if trouble:
        parts.append(f"{trouble} could not be checked")
    if not parts:
        return f"shelflife: all {len(results)} items fine."
    head = "shelflife: " + ", ".join(parts) + "."
    soonest = next(
        (
            r
            for r in sort_for_report(results, today)
            if r.status(today, threshold_days) in ("expired", "expiring")
        ),
        None,
    )
    if soonest is None:
        return head
    days = soonest.days_left(today)
    when = f"{-days} days ago" if days < 0 else ("today" if days == 0 else f"in {days} days")
    return f"{head} Soonest: {soonest.item.name} ({soonest.item.owner}) {when}."


def build_payload(results: list[Result], today: date, threshold_days: int) -> bytes:
    body = json.loads(render_json(results, today, threshold_days))
    line = summary_line(results, today, threshold_days)
    return json.dumps({"text": line, "content": line, **body}).encode("utf-8")


def post_json(url: str, body: bytes, timeout: float = DEFAULT_TIMEOUT) -> int:
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    with safe_opener().open(request, timeout=timeout) as response:  # noqa: S310
        return response.status


def send(
    url: str,
    results: list[Result],
    today: date,
    threshold_days: int,
    post: Poster = post_json,
) -> None:
    """POST the report to url. Raises WebhookError, with no URL in the message, on any failure."""
    problem = url_problem(url)
    if problem:
        raise WebhookError(f"webhook URL {problem}")
    body = build_payload(results, today, threshold_days)
    try:
        status = post(url, body, DEFAULT_TIMEOUT)
    except urllib.error.HTTPError as e:
        raise WebhookError(f"webhook returned HTTP {e.code}") from e
    except RedirectError as e:
        raise WebhookError("webhook redirected somewhere this tool refuses to follow") from e
    except urllib.error.URLError as e:
        raise WebhookError(f"webhook could not be reached: {e.reason}") from e
    except TimeoutError as e:
        raise WebhookError(f"webhook did not answer within {DEFAULT_TIMEOUT:g}s") from e
    except Exception as e:  # noqa: BLE001  (whatever it was, the URL must not leak in a traceback)
        raise WebhookError(f"webhook post failed: {type(e).__name__}") from e
    if not isinstance(status, int) or not 200 <= status < 300:
        raise WebhookError(f"webhook returned HTTP {status}")


def url_problem(url: str) -> str | None:
    """Why a webhook URL is unusable, or None. The webhook is the one place an operator types a
    URL, so it gets checked before anything is sent: HTTPS only (which also rules out file:// and
    plain-HTTP to a private address), and it has to have a host."""
    if not url or not url.strip():
        return "is empty"
    parts = urllib.parse.urlsplit(url.strip())
    if parts.scheme != "https":
        return "must start with https://"
    if not parts.hostname:
        return "has no host"
    return None
