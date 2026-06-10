"""verify primitive — MX/DNS deliverability checks (port of dns_check.py).

Syntax check (Pydantic already enforced on read) + null-MX detection (RFC
7505) + MX-or-A fallback (RFC 5321). SMTP mailbox probes are deliberately not
here: laptops' port 25 is almost always blocked and probes hurt reputation —
a future api-provider verifier can be added as a new subcommand if needed.
"""

from __future__ import annotations

import asyncio
import sys
from functools import lru_cache

import typer

from toolbox.core import events, io, models

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """verify primitive."""


@lru_cache(maxsize=4096)
def _domain_has_mail(domain: str, timeout: float = 5.0) -> tuple[bool, str]:
    """-> (deliverable?, reason). Cached per process."""
    import dns.exception
    import dns.resolver

    d = domain.lower().strip().rstrip(".")
    if not d:
        return False, "empty domain"
    resolver = dns.resolver.Resolver()
    resolver.lifetime = timeout
    try:
        answer = sorted(resolver.resolve(d, "MX"), key=lambda r: r.preference)
        targets = [r.exchange.to_text().rstrip(".") for r in answer]
        if len(targets) == 1 and answer[0].preference == 0 and targets[0] in ("", "."):
            return False, "null MX (RFC 7505)"
        if targets:
            return True, f"mx:{targets[0]}"
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        pass
    except dns.exception.Timeout:
        return False, "dns timeout"
    try:
        resolver.resolve(d, "A")
        return True, "a-record fallback (RFC 5321)"
    except Exception:
        return False, "no MX, no A"


@app.command()
def check(
    in_: str = typer.Option(..., "--in"),
    out: str = typer.Option(..., "--out"),
    concurrency: int = typer.Option(20, "--concurrency"),
    drop_unverified: bool = typer.Option(True, "--drop-unverified/--keep-unverified"),
):
    """contacts.csv -> verified.csv with verified/mx_ok/verify_reason columns."""
    rows = io.read_csv(in_, models.Contact)

    async def verify_all() -> list[models.VerifiedContact]:
        sem = asyncio.Semaphore(max(1, concurrency))

        async def one(c: models.Contact) -> models.VerifiedContact:
            domain = c.email.rsplit("@", 1)[-1]
            async with sem:
                ok, reason = await asyncio.to_thread(_domain_has_mail, domain)
            return models.VerifiedContact(**c.model_dump(), verified=ok, mx_ok=ok, verify_reason=reason)

        return list(await asyncio.gather(*(one(c) for c in rows)))

    verified = asyncio.run(verify_all())
    kept = [v for v in verified if v.verified] if drop_unverified else verified
    n = io.write_csv(out, kept)
    events.emit("verify.checked", total=len(verified), kept=n)
    typer.echo(f"verify.check: {n}/{len(verified)} deliverable")


if __name__ == "__main__":
    sys.exit(app())
