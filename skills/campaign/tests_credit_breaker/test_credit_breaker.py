"""Offline proof that the Hunter-credit-burn bug is fixed and cannot recur.

Nothing here touches the network or spends a Hunter credit: every Hunter call
(`_hunter_email_count`, `_hunter_domain_all`) is replaced with a fake, the LLM
niche/domain generators are faked, and the Supabase ledger is faked. We then
count how many times the *paid* call (`_hunter_domain_all`) is invoked — that
count is the credit spend, and the whole point of the breaker is to bound it.

Run (no real keys needed):
    cd /Users/shamitd/interns/toolbox
    uv run python -m pytest ../skills/campaign/tests_credit_breaker/ -v

Delete this folder after the fix is merged.
"""
from __future__ import annotations

import asyncio
import itertools

import pytest


# ---- fakes -------------------------------------------------------------

class _FakeLedger:
    """Stand-in for toolbox.core.ledger.Ledger — every contact is 'new'."""
    def __init__(self, *_a, **_k):
        pass

    async def check(self, _channel, _recipient):
        return "new"

    async def aclose(self):
        pass


def _valid_result(domain: str) -> dict:
    return {
        "email": f"ceo@{domain}",
        "first_name": "Test",
        "last_name": "Exec",
        "title": "CEO",
        "company": domain.split(".")[0].title(),
        "domain": domain,
        "email_score": 95,
        "email_status": "valid",
    }


def _install_common_fakes(monkeypatch, camp, tmp_path):
    """Patch out the LLM, the subcat cache location, and the ledger.

    Returns a dict of counters the test can assert on.
    """
    # Keep the persistent subcat cache inside the test's tmp dir.
    monkeypatch.setattr(camp, "_SUBCAT_DIR", tmp_path / "subcats")

    counters = {"subcat_calls": 0, "domain_gen_calls": 0}
    niche_seq = itertools.count(1)

    def fake_generate_subcategories(icp, count=25, exclude=None):
        # Always hand back a fresh, unique batch of niches. Without a breaker
        # this would let the pipeline generate niches forever.
        counters["subcat_calls"] += 1
        return [f"niche-{next(niche_seq)}" for _ in range(count)]

    def fake_generate_domains_for_subcat(subcat, count=20, exclude=None):
        counters["domain_gen_calls"] += 1
        # 5 unique domains per niche, namespaced by niche so they never repeat.
        return [f"{subcat}-d{i}.com" for i in range(5)]

    monkeypatch.setattr(camp, "generate_subcategories", fake_generate_subcategories)
    monkeypatch.setattr(camp, "generate_domains_for_subcat", fake_generate_domains_for_subcat)
    monkeypatch.setattr(camp.ledger, "Ledger", _FakeLedger)
    return counters


def _run_pipeline(camp, limit):
    return asyncio.run(camp.source_contacts_pipeline(
        "DTC luxury bedding", "hunter", "fake_key", "fake_session",
        limit=limit, min_score=80, label="Test",
    ))


# ---- 1. regression: the NameError is gone ------------------------------

def test_enrich_batch_returns_contact_without_error(monkeypatch):
    """Regression for the original bug. A domain with execs used to crash on the
    `_hunter_credits += ...` line (NameError), which got swallowed as an
    enrich_error and threw the contact away. That counter line is now gone, so a
    clean enrichment must keep the contact and emit no enrich_error. There must
    also be no stray reference to the deleted `_hunter_credits` symbol."""
    from skills.campaign import run as camp
    import httpx

    assert not hasattr(camp, "_hunter_credits"), "dead _hunter_credits symbol resurfaced"

    async def fake_count(_client, _key, _domain):
        return 5

    async def fake_all(_client, _key, domain, limit=10, executives_only=True):
        return [_valid_result(domain)]

    monkeypatch.setattr(camp.findemail_cli, "_hunter_email_count", fake_count)
    monkeypatch.setattr(camp.findemail_cli, "_hunter_domain_all", fake_all)

    errors: list = []
    monkeypatch.setattr(camp.events, "emit",
                        lambda name, **kw: errors.append(name) if name == "campaign.enrich_error" else None)

    async def go():
        async with httpx.AsyncClient() as client:
            stats: dict = {}
            contacts = await camp._enrich_batch(client, ["saatva.com"], "hunter",
                                                "fake_key", 80, stats=stats)
            return contacts, stats

    contacts, stats = asyncio.run(go())
    assert len(contacts) == 1                       # contact survived
    assert contacts[0].email == "ceo@saatva.com"
    assert errors == []                             # no enrich_error emitted
    assert stats["errors"] == 0


# ---- 2. THE BIG ONE: a systemic failure cannot run away ----------------

def test_pipeline_circuit_breaks_on_total_enrichment_failure(monkeypatch, tmp_path):
    """Simulate the exact failure mode that cost $15: every paid Hunter call
    raises. Without a breaker the pipeline generated 89+ niches and made 884
    paid calls. With the breaker it must abort after a bounded number of calls."""
    from skills.campaign import run as camp

    _install_common_fakes(monkeypatch, camp, tmp_path)
    paid_calls = {"n": 0}

    async def fake_count(_client, _key, _domain):
        return 5  # pretend every domain has execs, so we reach the paid call

    async def fake_all(_client, _key, _domain, limit=10, executives_only=True):
        paid_calls["n"] += 1
        raise RuntimeError("name '_hunter_credits' is not defined")  # the real bug

    monkeypatch.setattr(camp.findemail_cli, "_hunter_email_count", fake_count)
    monkeypatch.setattr(camp.findemail_cli, "_hunter_domain_all", fake_all)

    contacts = _run_pipeline(camp, limit=7)

    assert contacts == []                                   # nothing found, as expected
    # The breaker trips at _MAX_ENRICH_ERRORS_NO_PROGRESS (20). 5 domains/niche,
    # so it aborts well under 30 paid calls — not the hundreds we saw in prod.
    assert paid_calls["n"] <= camp._MAX_ENRICH_ERRORS_NO_PROGRESS + 5, (
        f"credit burn not bounded: {paid_calls['n']} paid calls")


# ---- 3. backstop: no-error infinite loop is also capped ----------------

def test_pipeline_niche_cap_stops_unbounded_generation(monkeypatch, tmp_path):
    """When enrichment errors never fire but nothing is ever found (every domain
    skipped by the free pre-check), the error breaker stays quiet. The niche
    hard cap must still stop the niche-generation loop."""
    from skills.campaign import run as camp

    counters = _install_common_fakes(monkeypatch, camp, tmp_path)

    async def fake_count(_client, _key, _domain):
        return 0  # no execs anywhere → email_count_skip, no paid call, no error

    async def fake_all(*_a, **_k):  # should never be called
        raise AssertionError("paid call made despite zero email-count")

    monkeypatch.setattr(camp.findemail_cli, "_hunter_email_count", fake_count)
    monkeypatch.setattr(camp.findemail_cli, "_hunter_domain_all", fake_all)

    contacts = _run_pipeline(camp, limit=7)

    assert contacts == []
    # Niche generation must stop at the cap, not spin forever.
    assert counters["domain_gen_calls"] <= camp._MAX_SOURCING_NICHES + 2, (
        f"niche loop not bounded: {counters['domain_gen_calls']} niches generated")


# ---- 4. healthy run still works and stops at the limit -----------------

def test_pipeline_happy_path_fills_and_stops(monkeypatch, tmp_path):
    """A working run finds contacts and stops near the limit without churning
    through extra niches."""
    from skills.campaign import run as camp

    counters = _install_common_fakes(monkeypatch, camp, tmp_path)
    paid_calls = {"n": 0}

    async def fake_count(_client, _key, _domain):
        return 5

    async def fake_all(_client, _key, domain, limit=10, executives_only=True):
        paid_calls["n"] += 1
        return [_valid_result(domain)]

    monkeypatch.setattr(camp.findemail_cli, "_hunter_email_count", fake_count)
    monkeypatch.setattr(camp.findemail_cli, "_hunter_domain_all", fake_all)

    # 5 domains/niche, so two niches land exactly on a limit of 10 — clear of the
    # _FILL_TOLERANCE early-exit (which would otherwise stop a limit of 7 at 5/7).
    contacts = _run_pipeline(camp, limit=10)

    assert len(contacts) == 10                      # target met exactly
    # Should not have ground through many niches to get there (5 domains/niche).
    assert counters["domain_gen_calls"] <= 5, (
        f"too many niches for a healthy run: {counters['domain_gen_calls']}")


# ---- 5. campaign-wide credit total spans the whole run -----------------

def test_run_all_reports_campaign_wide_total(monkeypatch):
    """The fix for per-sender attribution: run_all reports one authoritative
    total = last sender's account `after` minus first sender's `before`, not the
    sum of per-sender deltas of the shared, latently-updated counter."""
    from skills.campaign.server import executor

    sends: list = []

    async def fake_send(msg):
        sends.append(msg)

    # Two sequential senders against the shared account counter:
    #   sender 1: before=100 after=101   sender 2: before=101 after=114
    # Campaign-wide truth = 114 - 100 = 14.
    snapshots = [(100, 101), (101, 114)]
    idx = {"i": 0}

    async def fake_run_campaign(item, send_update, set_progress=None, usage=None):
        before, after = snapshots[idx["i"]]
        idx["i"] += 1
        if usage is not None:
            if usage.get("before") is None:
                usage["before"] = before
            usage["after"] = after
        return f"{item['from_name']}: done"

    monkeypatch.setattr(executor, "run_campaign", fake_run_campaign)
    plan = [{"from_name": "Armaan"}, {"from_name": "Ethan"}]
    asyncio.run(executor.run_all(plan, fake_send))

    assert any("Campaign total: 14 Hunter credits" in m for m in sends), sends
