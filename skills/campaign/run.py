#!/usr/bin/env python3
"""Campaign orchestrator: ICP description -> source leads -> enrich -> compose -> send.

Providers:
  hunter / apollo   API-based. Claude generates target domains from your ICP,
                    then the provider finds the decision-maker email per domain.
  clay / origami    CSV export. Export leads from the tool's UI, pass with --leads.
                    We compose and send from that list directly.

Experiment mode (--experiment):
  Leads are split 50/50. Claude generates a meaningfully different variant B.
  Reply rates are tracked per variant in Supabase. Use reply_report.py to see results.

Usage:
  python3 skills/campaign/run.py \\
    --icp "DTC health and wellness brands" \\
    --provider hunter \\
    --from shamit.dsouza@gmail.com \\
    --from-name "Shamit" \\
    --experiment \\
    --limit 20 \\
    --dry-run

  # Clay/Origami: export CSV first, then:
  python3 skills/campaign/run.py \\
    --leads my_export.csv \\
    --provider clay \\
    --from shamit.dsouza@gmail.com \\
    --from-name "Shamit"
"""

from __future__ import annotations

import argparse
import asyncio
import html as _html_module
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

# Allow running as a standalone script from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "toolbox" / "src"))

from toolbox.core import auth, config, events, io, ledger, models
from toolbox.core import llm as llm_mod
from toolbox.primitives.compose import lib as compose_lib
from toolbox.primitives.findemail import cli as findemail_cli
from toolbox.primitives.gmail import cli as gmail_cli
from skills.campaign import gog_auth, notion_sync


# ---- LLM helpers -------------------------------------------------------

class _DomainList(BaseModel):
    domains: list[str]


class _VariantTemplate(BaseModel):
    subject: str
    body: str


def generate_domains(icp: str, count: int = 30) -> list[str]:
    """Ask Claude for real company domains that match the ICP."""
    result = llm_mod.parse(
        f"List {count} real company website domains (e.g. 'glossier.com') that fit this "
        f"ideal customer profile: {icp}\n\n"
        "Return actual, real companies. Prefer DTC/e-commerce. No www prefix, no paths.",
        _DomainList,
    )
    return [d.strip().lower() for d in result.domains if "." in d.strip()]


def generate_variant_b(subject_a: str, body_a: str) -> tuple[str, str]:
    """Ask Claude to write a meaningfully different A/B variant."""
    result = llm_mod.parse(
        "You are an A/B testing expert for cold email outreach. Here is variant A:\n\n"
        f"Subject: {subject_a}\n\n{body_a}\n\n"
        "Write variant B that tests a distinctly different angle or tone. Same sender "
        "context (Stanford/Dartmouth students building AI tools for DTC brands). "
        "Subject must be different. Body must differ in structure or length. "
        "Use {{first_name}} and {{company}} template slots.",
        _VariantTemplate,
    )
    return result.subject, result.body


# ---- Lead sourcing / enrichment ----------------------------------------

def load_leads_csv(path: str, min_score: int = 0) -> list[models.Contact]:
    """Load a pre-exported Clay/Origami CSV into Contact objects."""
    rows = io.read_csv(path, models.Row)
    contacts: list[models.Contact] = []
    for r in rows:
        d = r.model_dump()
        # Clay exports sometimes put the company name in 'company' or 'brand'
        if not d.get("company") and d.get("brand"):
            d["company"] = d["brand"]
        try:
            contacts.append(models.Contact(**d))
        except (ValueError, TypeError) as e:
            events.emit("campaign.bad_lead", level="warn", row=str(d)[:120], reason=str(e))
    return contacts


async def _enrich_batch(
    client: httpx.AsyncClient,
    domains: list[str],
    provider: str,
    key: str,
    min_score: int,
) -> list[models.Contact]:
    """Enrich one batch of domains — returns contacts that passed the score filter."""
    domain_fn = (
        findemail_cli._apollo_domain if provider == "apollo" else findemail_cli._hunter_domain
    )
    contacts: list[models.Contact] = []
    sem = asyncio.Semaphore(3)

    async def one(domain: str) -> None:
        async with sem:
            try:
                res = await domain_fn(client, key, domain, limit=10, executives_only=True)
            except Exception as e:
                msg = str(e)
                if "429" in msg:
                    events.emit("campaign.rate_limited", level="warn", domain=domain)
                else:
                    events.emit("campaign.enrich_error", level="warn", domain=domain, reason=msg[:120])
                return
        if not res or not res.get("email"):
            events.emit("campaign.no_contact", domain=domain)
            return
        if int(res.get("email_score") or 0) < min_score:
            events.emit("campaign.low_score", domain=domain, score=res.get("email_score"))
            return
        try:
            contacts.append(models.Contact(
                email=res["email"],
                first_name=res.get("first_name", ""),
                last_name=res.get("last_name", ""),
                title=res.get("title", ""),
                company=domain.split(".")[0].title(),
                domain=domain,
            ))
        except ValueError as e:
            events.emit("campaign.bad_email", level="warn", email=res.get("email"), reason=str(e))

    await asyncio.gather(*(one(d) for d in domains))
    return contacts


async def enrich_domains(
    domains: list[str],
    provider: str,
    key: str,
    min_score: int = 80,
) -> list[models.Contact]:
    """Enrich all domains at once. Used when --domains is provided (pool already fixed)."""
    async with httpx.AsyncClient(timeout=60) as client:
        return await _enrich_batch(client, domains, provider, key, min_score)


async def source_contacts_incremental(
    domains: list[str],
    provider: str,
    key: str,
    session_token: str,
    limit: int | None,
    min_score: int = 80,
    batch_size: int = 20,
) -> list[models.Contact]:
    """Enrich domains in batches, ledger-checking each batch before continuing.

    Stops as soon as `limit` new contacts are accumulated. This avoids spending
    enrichment credits on contacts that will be discarded after ledger dedup.
    """
    accumulated: list[models.Contact] = []
    ldg = ledger.Ledger(session_token)

    async with httpx.AsyncClient(timeout=60) as client:
        for i in range(0, len(domains), batch_size):
            batch = domains[i : i + batch_size]
            raw = await _enrich_batch(client, batch, provider, key, min_score)

            # Ledger-check this batch concurrently.
            sem = asyncio.Semaphore(10)
            new_in_batch: list[tuple[int, models.Contact]] = []

            async def check_one(idx: int, c: models.Contact) -> None:
                async with sem:
                    status = await ldg.check("email", c.email)
                if status == "new":
                    new_in_batch.append((idx, c))

            await asyncio.gather(*(check_one(j, c) for j, c in enumerate(raw)))
            new_in_batch.sort(key=lambda x: x[0])
            accumulated.extend(c for _, c in new_in_batch)

            enriched_so_far = i + len(batch)
            print(
                f"  batch {i // batch_size + 1}: {len(raw)} found, "
                f"{len(new_in_batch)} new — {len(accumulated)} total "
                f"({enriched_so_far}/{len(domains)} domains used)"
            )

            if limit and len(accumulated) >= limit:
                break

    await ldg.aclose()

    if limit:
        accumulated = accumulated[:limit]
    return accumulated


# ---- Ledger pre-check --------------------------------------------------

async def _filter_new_contacts(contacts: list[models.Contact], session_token: str) -> list[models.Contact]:
    """Remove contacts already in the ledger so --limit counts actual sends."""
    ldg = ledger.Ledger(session_token)
    sem = asyncio.Semaphore(10)
    results: list[tuple[int, models.Contact]] = []

    async def check_one(i: int, c: models.Contact) -> None:
        async with sem:
            status = await ldg.check("email", c.email)
        if status == "new":
            results.append((i, c))

    try:
        await asyncio.gather(*(check_one(i, c) for i, c in enumerate(contacts)))
    finally:
        await ldg.aclose()

    results.sort(key=lambda x: x[0])
    return [c for _, c in results]


# ---- ICP mix -----------------------------------------------------------

_ICP_MIX_PATH = Path(__file__).parent / "icp_mix.toml"


def _load_mix() -> list[dict]:
    with open(_ICP_MIX_PATH, "rb") as f:
        data = tomllib.load(f)
    return data["segments"]


def _mix_quotas(limit: int, segments: list[dict]) -> list[tuple[dict, int]]:
    """Return (segment, quota) pairs that sum exactly to limit."""
    raw = [(s, s["weight"] * limit) for s in segments]
    quotas = [(s, int(q)) for s, q in raw]
    remainder = limit - sum(q for _, q in quotas)
    # Distribute leftover slots to segments with the largest fractional parts.
    fracs = sorted(range(len(raw)), key=lambda i: -(raw[i][1] % 1))
    for i in range(remainder):
        seg, q = quotas[fracs[i]]
        quotas[fracs[i]] = (seg, q + 1)
    return [(s, q) for s, q in quotas if q > 0]


async def _source_from_mix(
    provider: str,
    key: str,
    session_token: str,
    limit: int,
    from_name: str = "",
    min_score: int = 80,
) -> list[models.OutboxRow]:
    """Source and compose outbox rows across segments per icp_mix.toml."""
    segments = _load_mix()
    quotas = _mix_quotas(limit, segments)
    all_rows: list[models.OutboxRow] = []

    for i, (seg, quota) in enumerate(quotas):
        if i > 0:
            await asyncio.sleep(2)  # avoid Hunter/Apollo per-minute rate limits
        label = seg["label"]
        icp = seg["icp"]
        template_path = _ICP_MIX_PATH.parent / seg["template_a"]
        segment_phrase = seg.get("segment_phrase", label.lower())

        print(f"\n[{label}] target: {quota}")
        domain_count = max(30, quota * 3)
        domains = generate_domains(icp, count=domain_count)
        print(f"  {len(domains)} domains generated")
        contacts = await source_contacts_incremental(
            domains, provider, key, session_token,
            limit=quota, min_score=min_score,
        )
        print(f"  {len(contacts)} contacts sourced")
        subject_t, body_t = load_template(str(template_path))
        rows = compose_outbox(contacts, subject_t, body_t, from_name,
                              extra_values={"segment_phrase": segment_phrase})
        all_rows.extend(rows)

    return all_rows


# ---- Compose -----------------------------------------------------------

def load_template(path: str) -> tuple[str, str]:
    return compose_lib.parse_template(Path(path).read_text(encoding="utf-8"))


def _html_to_text(html: str) -> str:
    """Strip HTML tags to produce a plain-text fallback for email clients."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = _html_module.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def compose_outbox(
    contacts: list[models.Contact],
    subject_t: str,
    body_t: str,
    from_name: str = "",
    extra_values: dict | None = None,
) -> list[models.OutboxRow]:
    is_html = body_t.lstrip().startswith("<")
    rows: list[models.OutboxRow] = []
    for c in contacts:
        values = {**c.model_dump(), "from_name": from_name}
        if extra_values:
            values.update(extra_values)
        # 'company' slot: fall back to domain stem if missing
        if not values.get("company") and values.get("domain"):
            values["company"] = values["domain"].split(".")[0].title()
        try:
            rendered_body = compose_lib.render(body_t, values)
            body = _html_to_text(rendered_body) if is_html else rendered_body
            body_html = rendered_body if is_html else ""
            rows.append(models.OutboxRow(
                email=c.email,
                subject=compose_lib.render(subject_t, values),
                body=body,
                body_html=body_html,
                **{k: v for k, v in values.items()
                   if k not in ("email", "subject", "body", "body_html")
                   and isinstance(v, (str, int, float, bool))},
            ))
        except compose_lib.TemplateError as e:
            events.emit("campaign.compose_drop", level="warn", email=c.email, reason=str(e))
    return rows


# ---- Send --------------------------------------------------------------

async def _send_batch(
    outbox: list[models.OutboxRow],
    from_: str,
    from_name: str,
    run_id: str,
    run_dir: str,
    dry_run: bool,
) -> dict:
    if dry_run:
        return {"sent": 0, "dry_run": len(outbox), "skipped_ledger": 0, "suppressed": 0,
                "failed": 0, "resumed_skip": 0, "quota_aborted": 0}

    # Get token from gog once; inject so gmail_cli._send_all picks it up.
    token = gog_auth.get_access_token(from_)
    os.environ["TOOLBOX_TOKEN_GMAIL"] = token
    try:
        return await gmail_cli._send_all(
            rows=outbox,
            run_dir=run_dir,
            run_id=run_id,
            skill="campaign",
            from_=from_,
            from_name=from_name,
            reply_to="",
            cc="",
            concurrency=5,
            allow_recontact=False,
            sent_already=set(),
        )
    finally:
        os.environ.pop("TOOLBOX_TOKEN_GMAIL", None)


# ---- Campaign log (for reply_scan.py) ----------------------------------

def write_campaign_log(log_path: str, entries: list[dict]) -> None:
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


# ---- Supabase campaigns write ------------------------------------------

def _write_campaign_to_supabase(
    run_id: str, sender: str, sender_email: str, provider: str,
    template_name: str, icp: str, experiment: bool, sent_count: int,
) -> None:
    try:
        session = auth.session_token()
        r = httpx.post(
            f"{config.supabase_url()}/rest/v1/campaigns",
            headers={
                "apikey": config.supabase_anon_key(),
                "Authorization": f"Bearer {session}",
                "Content-Type": "application/json",
                "Prefer": "resolution=ignore-duplicates,return=minimal",
            },
            json={
                "run_id": run_id, "sender": sender, "sender_email": sender_email,
                "provider": provider, "template_name": template_name,
                "icp_description": icp, "experiment": experiment,
                "sent_count": sent_count,
            },
            timeout=30,
        )
        if r.status_code not in (200, 201):
            events.emit("campaigns.write_failed", level="warn",
                        status=r.status_code, body=r.text[:200])
    except Exception as e:
        events.emit("campaigns.write_error", level="warn", reason=str(e)[:200])


# ---- Finalize (shared by mix and single-ICP paths) --------------------

def _finalize(
    args: argparse.Namespace,
    run_id: str,
    sender_name: str,
    total_sent: int,
    total_dry: int,
    template_name: str,
    icp_label: str,
    outbox_a: list[models.OutboxRow],
    outbox_b: list[models.OutboxRow],
    sent_at: str,
    counts_a: dict,
    counts_b: dict,
) -> None:
    if not args.dry_run:
        _write_campaign_to_supabase(
            run_id=run_id,
            sender=sender_name,
            sender_email=args.from_,
            provider=args.provider,
            template_name=template_name,
            icp=icp_label,
            experiment=args.experiment,
            sent_count=total_sent,
        )

    notion_page_id = ""
    if not args.dry_run:
        notion_page_id = notion_sync.create_campaign_row(
            run_id=run_id,
            sender=sender_name,
            date=datetime.now().strftime("%Y-%m-%d"),
            provider=args.provider,
            template_name=template_name,
            icp=icp_label,
            experiment=args.experiment,
            sent_count=total_sent,
        ) or ""
        if notion_page_id:
            print(f"Notion : https://app.notion.com/p/{notion_page_id.replace('-', '')}")

    default_log_dir = Path.home() / ".blackwell" / "campaigns"
    default_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.log or str(default_log_dir / f"campaign_{run_id[:8]}.jsonl")
    meta_entry = {
        "_meta": True, "run_id": run_id, "sender": sender_name,
        "sender_email": args.from_, "provider": args.provider,
        "template": template_name, "icp": icp_label,
        "experiment": args.experiment, "sent_count": total_sent,
        "notion_page_id": notion_page_id, "sent_at": sent_at,
    }
    contact_entries = (
        [{"email": r.email, "run_id": run_id, "variant": "a", "sent_at": sent_at}
         for r in outbox_a]
        + [{"email": r.email, "run_id": run_id, "variant": "b", "sent_at": sent_at}
           for r in outbox_b]
    )
    write_campaign_log(log_path, [meta_entry] + contact_entries)

    print(f"\nResult: sent={total_sent}" + (f", dry_run_preview={total_dry}" if args.dry_run else ""))
    print(f"Log   : {log_path}")
    print(f"Replies: python3 skills/campaign/reply_scan.py --log {log_path}")
    print(f"Report : python3 skills/campaign/reply_report.py --log {log_path}")


# ---- Preflight ---------------------------------------------------------

def _preflight(from_: str, provider: str) -> None:
    """Validate all credentials before spending any API credits.

    Exits with a clear message on the first failure so the user knows
    exactly what to fix before the run starts.
    """
    errors: list[str] = []

    # 1. Supabase session
    try:
        auth.session_token()
    except Exception as e:
        errors.append(f"Supabase session invalid: {e}\n  Fix: toolbox auth login")

    # 2. Provider key
    if provider not in ("clay", "origami"):
        try:
            key = auth.get_token(provider)
            if not key:
                raise ValueError("empty token")
        except Exception as e:
            env_var = f"TOOLBOX_TOKEN_{provider.upper()}"
            errors.append(
                f"{provider} API key missing or invalid: {e}\n"
                f"  Fix: set {env_var} in credentials/.env"
            )

    # 3. gog Gmail token
    try:
        token = gog_auth.get_access_token(from_)
        if not token:
            raise ValueError("empty token")
        # Probe Gmail API with the token — a bad token returns 401 immediately.
        r = httpx.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.status_code == 401:
            raise ValueError("token rejected by Gmail (401)")
    except Exception as e:
        errors.append(
            f"Gmail (gog) auth failed for {from_}: {e}\n"
            f"  Fix: gog auth add {from_} --services gmail"
        )

    # 4. Notion token (optional — only warn)
    notion_token = os.environ.get("NOTION_TOKEN", "").strip()
    if notion_token:
        r = httpx.get(
            "https://api.notion.com/v1/users/me",
            headers={
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28",
            },
            timeout=10,
        )
        if r.status_code == 401:
            print("Warning: NOTION_TOKEN is invalid — Notion sync will be skipped")

    if errors:
        print("\nPreflight failed — fix these before running:\n")
        for err in errors:
            print(f"  {err}\n")
        sys.exit(1)

    print("Preflight OK")


# ---- Main --------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--icp", default="",
                        help="ICP description: Claude generates target domains from this")
    parser.add_argument("--provider", default="hunter",
                        choices=["hunter", "apollo", "clay", "origami"],
                        help="Lead source (clay/origami require --leads CSV)")
    parser.add_argument("--leads", default="",
                        help="Pre-exported leads CSV from Clay or Origami (has email column)")
    parser.add_argument("--domains", default="",
                        help="Pre-built domains CSV (skips ICP domain generation)")
    parser.add_argument("--template",
                        default=str(Path(__file__).parent / "template_a.md"),
                        help="Template file (frontmatter subject + body)")
    parser.add_argument("--from", dest="from_", required=True,
                        help="Gmail address to send from")
    parser.add_argument("--from-name", default="",
                        help="Display name in the From header")
    parser.add_argument("--experiment", action="store_true",
                        help="A/B mode: split 50/50, Claude writes variant B")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max contacts to send to (0 = no cap)")
    parser.add_argument("--min-score", type=int, default=80,
                        help="Minimum Hunter/Apollo email confidence (0-100)")
    parser.add_argument("--log", default="",
                        help="Campaign log path for reply tracking (default: /tmp/campaign_<id>.jsonl)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be sent without actually sending")
    args = parser.parse_args()

    if args.provider in ("clay", "origami") and not args.leads:
        parser.error(f"--provider {args.provider} requires --leads <exported_csv>")
    if not args.icp and not args.leads and not args.domains:
        if not _ICP_MIX_PATH.exists():
            parser.error(
                "Need one of: --icp TEXT, --leads FILE, or --domains FILE\n"
                f"(or add {_ICP_MIX_PATH} to use the default ICP mix)"
            )

    _preflight(args.from_, args.provider)

    run_id = str(uuid.uuid4())
    run_dir = tempfile.mkdtemp(prefix=f"campaign_{run_id[:8]}_")
    print(f"run_id : {run_id}")
    print(f"run_dir: {run_dir}")

    # 1. Source contacts --------------------------------------------------
    session_token = auth.session_token()

    if args.leads:
        # CSV import: all contacts are known upfront, just ledger-filter.
        contacts = load_leads_csv(args.leads, min_score=args.min_score)
        print(f"Loaded {len(contacts)} contacts from {args.leads}")
        print("Checking ledger...")
        contacts = asyncio.run(_filter_new_contacts(contacts, session_token))
        print(f"  {len(contacts)} new (not yet contacted)")
        if args.limit:
            contacts = contacts[: args.limit]
    elif args.domains:
        # Fixed domain list: enrich all upfront, then ledger-filter.
        domain_rows = io.read_csv(args.domains, models.Domain)
        domains = [r.domain for r in domain_rows]
        print(f"Loaded {len(domains)} domains from {args.domains}")
        key = auth.get_token(args.provider)
        print(f"Enriching via {args.provider}...")
        contacts = asyncio.run(
            enrich_domains(domains, args.provider, key, min_score=args.min_score)
        )
        print(f"  {len(contacts)} contacts found")
        print("Checking ledger...")
        contacts = asyncio.run(_filter_new_contacts(contacts, session_token))
        print(f"  {len(contacts)} new (not yet contacted)")
        if args.limit:
            contacts = contacts[: args.limit]
    elif args.icp:
        # Focused ICP path: generate a large domain pool, enrich + ledger-check
        # in batches of 20, stop as soon as --limit new contacts are found.
        domain_count = max(60, (args.limit or 30) * 3)
        print(f"Generating domains for: {args.icp[:80]}")
        domains = generate_domains(args.icp, count=domain_count)
        print(f"  {len(domains)} domains generated")
        key = auth.get_token(args.provider)
        print(f"Enriching via {args.provider} (incremental, stop at limit)...")
        contacts = asyncio.run(
            source_contacts_incremental(
                domains, args.provider, key, session_token,
                limit=args.limit, min_score=args.min_score,
            )
        )
    else:
        # Default: distribute contacts across segments per icp_mix.toml.
        # Each segment uses its own template; outbox rows are returned pre-composed.
        limit = args.limit or 20
        key = auth.get_token(args.provider)
        print(f"Sourcing {limit} contacts across ICP mix ({_ICP_MIX_PATH.name})...")
        outbox_a = asyncio.run(
            _source_from_mix(
                args.provider, key, session_token,
                limit=limit, from_name=args.from_name, min_score=args.min_score,
            )
        )
        outbox_b = []
        print(f"\nComposed: {len(outbox_a)} contacts across all segments")
        if not outbox_a:
            print("No new contacts — exiting.")
            sys.exit(0)
        # Skip the standard compose block below.
        if args.dry_run:
            print("\n[dry-run] Sample sends:")
            for row in outbox_a[:5]:
                print(f"  TO: {row.email}")
                print(f"      {row.subject}")
            print()
        sent_at = datetime.now(UTC).isoformat()
        counts_a = asyncio.run(
            _send_batch(outbox_a, args.from_, args.from_name, run_id, run_dir, args.dry_run)
        )
        counts_b = {}
        total_sent = counts_a.get("sent", 0)
        total_dry = counts_a.get("dry_run", 0)
        template_name = "icp_mix"
        sender_name = args.from_name or args.from_.split("@")[0].title()
        icp_label = "ICP mix"
        _finalize(args, run_id, sender_name, total_sent, total_dry, template_name,
                  icp_label, outbox_a, outbox_b, sent_at, counts_a, counts_b)
        return

    if not contacts:
        print("No new contacts — exiting.")
        sys.exit(0)

    # 2. Load template A --------------------------------------------------
    subject_a, body_a = load_template(args.template)

    # 3. Experiment split -------------------------------------------------
    if args.experiment:
        mid = max(1, len(contacts) // 2)
        contacts_a, contacts_b = contacts[:mid], contacts[mid:]
        print("Generating variant B...")
        subject_b, body_b = generate_variant_b(subject_a, body_a)
        print(f"  Variant B subject: {subject_b}")
    else:
        contacts_a, contacts_b = contacts, []
        subject_b = body_b = ""

    # 4. Compose ----------------------------------------------------------
    outbox_a = compose_outbox(contacts_a, subject_a, body_a, from_name=args.from_name)
    outbox_b = (
        compose_outbox(contacts_b, subject_b, body_b, from_name=args.from_name)
        if contacts_b else []
    )
    print(f"Composed: {len(outbox_a)} variant-A, {len(outbox_b)} variant-B")

    if args.dry_run:
        print("\n[dry-run] Sample sends:")
        for row in (outbox_a + outbox_b)[:5]:
            print(f"  TO: {row.email}")
            print(f"      {row.subject}")
        print()

    # 5. Send -------------------------------------------------------------
    sent_at = datetime.now(UTC).isoformat()
    counts_a = asyncio.run(
        _send_batch(outbox_a, args.from_, args.from_name, run_id, run_dir, args.dry_run)
    )
    counts_b = (
        asyncio.run(
            _send_batch(outbox_b, args.from_, args.from_name, run_id, run_dir, args.dry_run)
        )
        if outbox_b else {}
    )

    total_sent = counts_a.get("sent", 0) + counts_b.get("sent", 0)
    total_dry = counts_a.get("dry_run", 0) + counts_b.get("dry_run", 0)
    template_name = Path(args.template).stem
    sender_name = args.from_name or args.from_.split("@")[0].title()
    _finalize(args, run_id, sender_name, total_sent, total_dry, template_name,
              args.icp, outbox_a, outbox_b, sent_at, counts_a, counts_b)


if __name__ == "__main__":
    main()
