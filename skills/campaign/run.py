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
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

# Allow running as a standalone script from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "toolbox" / "src"))

from toolbox.core import auth, config, events, io, models
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


def generate_domains(icp: str, count: int = 20) -> list[str]:
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


async def enrich_domains(
    domains: list[str],
    provider: str,
    key: str,
    min_score: int = 80,
) -> list[models.Contact]:
    """domains -> decision-maker contacts via Hunter or Apollo domain search."""
    domain_fn = (
        findemail_cli._apollo_domain if provider == "apollo" else findemail_cli._hunter_domain
    )
    contacts: list[models.Contact] = []
    sem = asyncio.Semaphore(5)

    async with httpx.AsyncClient(timeout=60) as client:
        async def one(domain: str) -> None:
            async with sem:
                res = await domain_fn(client, key, domain, limit=10, executives_only=True)
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


# ---- Compose -----------------------------------------------------------

def load_template(path: str) -> tuple[str, str]:
    return compose_lib.parse_template(Path(path).read_text(encoding="utf-8"))


def compose_outbox(
    contacts: list[models.Contact],
    subject_t: str,
    body_t: str,
    from_name: str = "",
) -> list[models.OutboxRow]:
    rows: list[models.OutboxRow] = []
    for c in contacts:
        values = {**c.model_dump(), "from_name": from_name}
        # 'company' slot: fall back to domain stem if missing
        if not values.get("company") and values.get("domain"):
            values["company"] = values["domain"].split(".")[0].title()
        try:
            rows.append(models.OutboxRow(
                email=c.email,
                subject=compose_lib.render(subject_t, values),
                body=compose_lib.render(body_t, values),
                **{k: v for k, v in values.items()
                   if k not in ("email", "subject", "body")
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
        parser.error("Need one of: --icp TEXT, --leads FILE, or --domains FILE")

    run_id = str(uuid.uuid4())
    run_dir = tempfile.mkdtemp(prefix=f"campaign_{run_id[:8]}_")
    print(f"run_id : {run_id}")
    print(f"run_dir: {run_dir}")

    # 1. Source contacts --------------------------------------------------
    if args.leads:
        contacts = load_leads_csv(args.leads, min_score=args.min_score)
        print(f"Loaded {len(contacts)} contacts from {args.leads}")
    else:
        if args.domains:
            domain_rows = io.read_csv(args.domains, models.Domain)
            domains = [r.domain for r in domain_rows]
            print(f"Loaded {len(domains)} domains from {args.domains}")
        else:
            print(f"Generating domains for: {args.icp[:80]}")
            domains = generate_domains(args.icp)
            print(f"  {len(domains)} domains: {', '.join(domains[:6])}{'...' if len(domains) > 6 else ''}")

        key = auth.get_token(args.provider)
        print(f"Enriching via {args.provider}...")
        contacts = asyncio.run(
            enrich_domains(domains, args.provider, key, min_score=args.min_score)
        )
        print(f"  {len(contacts)} contacts found")

    if args.limit:
        contacts = contacts[: args.limit]

    if not contacts:
        print("No contacts — exiting.")
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

    # 6. Write to Supabase campaigns table ------------------------------------
    template_name = Path(args.template).stem
    sender_name = args.from_name or args.from_.split("@")[0].title()
    if not args.dry_run:
        _write_campaign_to_supabase(
            run_id=run_id,
            sender=sender_name,
            sender_email=args.from_,
            provider=args.provider,
            template_name=template_name,
            icp=args.icp,
            experiment=args.experiment,
            sent_count=total_sent,
        )

    # 7. Write to Notion ------------------------------------------------------
    notion_page_id = ""
    if not args.dry_run:
        notion_page_id = notion_sync.create_campaign_row(
            run_id=run_id,
            sender=sender_name,
            date=datetime.now().strftime("%Y-%m-%d"),
            provider=args.provider,
            template_name=template_name,
            icp=args.icp,
            experiment=args.experiment,
            sent_count=total_sent,
        ) or ""
        if notion_page_id:
            print(f"Notion : https://app.notion.com/p/{notion_page_id.replace('-', '')}")

    # 8. Write campaign log (for reply_scan.py) --------------------------------
    default_log_dir = Path.home() / ".blackwell" / "campaigns"
    default_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.log or str(default_log_dir / f"campaign_{run_id[:8]}.jsonl")
    meta_entry = {
        "_meta": True, "run_id": run_id, "sender": sender_name,
        "sender_email": args.from_, "provider": args.provider,
        "template": template_name, "icp": args.icp,
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


if __name__ == "__main__":
    main()
