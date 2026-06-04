"""Human-readable live progress for a research run.

``format_event`` turns one Evidence Record into a single status line; the CLI
streams these to stderr as they happen so a real run is legible.
"""

from __future__ import annotations

import sys

from .evidence import EvidenceRecord

__all__ = ["format_event", "stderr_printer"]


def _host(url: str) -> str:
    try:
        return url.split("/")[2] if "://" in url else url
    except Exception:
        return url


def format_event(rec: EvidenceRecord) -> str:
    host = _host(rec.url)
    ms = f"{rec.elapsed_ms} ms"
    if rec.bypassed:
        return f"  🛡️  {host}  🧱 {rec.bot_wall} → ✅ bypassed   {ms}"
    if rec.escalated:
        return f"  ⚠️  {host}  🧱 {rec.bot_wall} → escalation failed   {ms}"
    if rec.bot_wall:
        return f"  •  {host}  🧱 {rec.bot_wall} (kept plain)   {ms}"
    return f"  ✓  {host}  open page   {ms}"


def stderr_printer(rec: EvidenceRecord) -> None:
    print(format_event(rec), file=sys.stderr, flush=True)
