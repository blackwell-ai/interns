"""GEO test command — preview the real AI-visibility email for live brands.

The wizard's normal preview (agent.render_sample) runs BEFORE any brand is
sourced, so it fills placeholder values and cannot show the per-brand
{{personal_line}} — that line is generated at send time, per contact. This
command closes that gap: given a niche or a specific domain, it sources a
couple of real live brands, runs the exact visibility.personalize check the
send path uses, and renders the finished email so the user can read the actual
comparison line before committing to a campaign. Read-only: sends nothing,
spends no Hunter credit (StoreLeads sourcing + one LLM call per brand only).

Trigger in Slack: "@wizard geo test women's lingerie" or
"@wizard geo test orange-lingerie.com".
"""
from __future__ import annotations

import re

from skills.campaign import storeleads, visibility

from . import agent

# Strip the command verb so the remainder is the niche or domain to test.
_TRIGGER_RE = re.compile(
    r"^\s*(geo\s*test|test\s*geo|geo\s*preview|test\s*ai\s*visibility)\b[:\s]*",
    re.IGNORECASE)
_DOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$", re.IGNORECASE)

# How many live brands to show for a niche test. Small on purpose: this is a
# copy check, not a campaign.
_SAMPLE = 2


def is_geo_test(text: str) -> bool:
    return bool(_TRIGGER_RE.search(text or ""))


def _argument(text: str) -> str:
    return _TRIGGER_RE.sub("", text or "", count=1).strip().strip("?.! ")


def _company_of(domain: str) -> str:
    stem = domain.split(".")[0]
    return stem.replace("-", " ").replace("_", " ").title()


async def _brands_for(arg: str) -> tuple[list[str], str]:
    """Return (domains, niche_hint). A domain argument tests that exact brand; a
    niche argument sources a couple of real live stores from StoreLeads."""
    arg = arg.strip()
    if _DOMAIN_RE.match(arg):
        return [arg.lower().removeprefix("www.")], ""
    if not storeleads.available():
        return [], arg
    try:
        domains, _cursor = await storeleads.search_domains(
            {}, q=arg, page_size=_SAMPLE)
    except Exception:  # noqa: BLE001 — a failed source is reported, not raised
        return [], arg
    return domains[:_SAMPLE], arg


async def run(text: str, reply) -> None:
    """Handle a 'geo test ...' command: source, check, render, post. `reply` is a
    thread-bound async callable (text, blocks)."""
    arg = _argument(text)
    if not arg:
        await reply(
            ":mage: Tell me what to test. Try `geo test women's lingerie` or "
            "`geo test orange-lingerie.com`.")
        return

    await reply(f":crystal_ball: Checking how brands show up in AI search for "
                f"*{arg}*. One moment...")

    domains, hint = await _brands_for(arg)
    if not domains:
        await reply(
            "I could not source a live brand for that. Give me a specific "
            "domain to test, e.g. `geo test orange-lingerie.com`.")
        return

    sender = agent.SENDERS[0]
    run_stub = {
        "template": agent.AI_VISIBILITY_TEMPLATE,
        "email": sender["email"],
        "from_name": sender["from_name"],
    }

    for domain in domains:
        company = _company_of(domain)
        line = await visibility.personalize(company, hint or company, domain=domain)
        subject, body = agent.render_sample(
            run_stub, first_name="there", company=company,
            extra={"personal_line": line})
        await reply(f"*{company}*  ({domain})\n"
                    f"*Subject:* {subject}\n\n{body}")

    await reply("_This is the real send-time personalization. Nothing was sent. "
                "Happy with the copy? Start a campaign the usual way._")
