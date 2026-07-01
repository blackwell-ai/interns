"""Offline tests for the deterministic email divider (agent._divide).

The LLM (agent.plan) is never called here — we feed _divide the intent directly,
so these run free and fast. Delete this folder after merge.

    cd /Users/shamitd/interns/toolbox
    uv run python -m pytest ../skills/campaign/tests_credit_breaker/ -v
"""
from __future__ import annotations


def _defaults():
    # A representative daily ICP mix (free text now — no preset segments).
    return [
        {"label": "DTC brands and retailers", "icp": "DTC brands", "weight": 0.40},
        {"label": "3PL and warehouses", "icp": "3PLs", "weight": 0.25},
        {"label": "Manufacturing", "icp": "manufacturers", "weight": 0.25},
        {"label": "Agent transaction companies", "icp": "agentic commerce", "weight": 0.05},
        {"label": "Inventory management systems", "icp": "inventory software", "weight": 0.05},
    ]


# ---- small campaigns consolidate to one sender -------------------------

def test_small_campaign_uses_one_sender_one_run():
    from skills.campaign.wizard import agent

    runs, deferred = agent._divide(10, _defaults())
    assert deferred == 0
    assert sum(r["n_emails"] for r in runs) == 10        # no emails lost to rounding
    assert len({r["sender_key"] for r in runs}) == 1     # exactly one sender
    assert len(runs) == 1                                # collapsed to one run (MIN_BATCH)
    assert runs[0]["sender_key"] == "armaan"             # fills the first sender first


def test_explicit_single_icp_is_respected():
    from skills.campaign.wizard import agent

    runs, deferred = agent._divide(30, [{"label": "Agent transaction companies", "weight": 1.0}])
    assert deferred == 0
    assert sum(r["n_emails"] for r in runs) == 30
    assert {r["icp_label"] for r in runs} == {"Agent transaction companies"}
    assert len({r["sender_key"] for r in runs}) == 1


# ---- the dominant case: large campaigns spread across senders ----------

def test_large_campaign_spreads_across_senders_under_cap():
    from skills.campaign.wizard import agent

    runs, deferred = agent._divide(2000, _defaults())
    assert deferred == 0
    assert sum(r["n_emails"] for r in runs) == 2000

    per_sender: dict = {}
    for r in runs:
        per_sender[r["sender_key"]] = per_sender.get(r["sender_key"], 0) + r["n_emails"]
    assert len(per_sender) == 3                                   # ceil(2000/800) = 3 senders
    assert all(v <= agent.PER_ACCOUNT_DAILY_CAP for v in per_sender.values())
    assert max(per_sender.values()) - min(per_sender.values()) <= 1  # evenly split


def test_two_thousand_uses_minimum_senders_not_all_when_fewer_fit():
    from skills.campaign.wizard import agent

    # 800 fits in exactly one sender at the cap — must not fan out to 3.
    runs, deferred = agent._divide(800, _defaults())
    assert deferred == 0
    assert sum(r["n_emails"] for r in runs) == 800
    assert len({r["sender_key"] for r in runs}) == 1
    # 801 tips into a second sender.
    runs2, _ = agent._divide(801, _defaults())
    assert len({r["sender_key"] for r in runs2}) == 2


# ---- over-capacity: cap and warn ---------------------------------------

def test_over_capacity_caps_and_reports_deferred():
    from skills.campaign.wizard import agent

    cap_total = len(agent.SENDERS) * agent.PER_ACCOUNT_DAILY_CAP  # 2400
    runs, deferred = agent._divide(3000, _defaults())
    assert deferred == 3000 - cap_total                           # 600 deferred
    assert sum(r["n_emails"] for r in runs) == cap_total          # only capacity sent
    per_sender: dict = {}
    for r in runs:
        per_sender[r["sender_key"]] = per_sender.get(r["sender_key"], 0) + r["n_emails"]
    assert all(v == agent.PER_ACCOUNT_DAILY_CAP for v in per_sender.values())  # each maxed


# ---- invariants --------------------------------------------------------

def test_no_run_below_min_batch_unless_collapsed():
    from skills.campaign.wizard import agent

    for total in (10, 25, 50, 120, 667, 800, 2000):
        runs, _ = agent._divide(total, _defaults())
        for r in runs:
            assert r["n_emails"] >= agent.MIN_BATCH or len(runs) == 1, (
                f"run below MIN_BATCH at total={total}: {r}")


def test_allocate_sums_exactly():
    from skills.campaign.wizard import agent

    for total in (0, 1, 7, 10, 13, 100, 667, 2000):
        counts = agent._allocate(total, [0.40, 0.25, 0.25, 0.05, 0.05])
        assert sum(counts) == total


def test_zero_total_yields_nothing():
    from skills.campaign.wizard import agent

    runs, deferred = agent._divide(0, _defaults())
    assert runs == []
    assert deferred == 0


def test_every_run_has_executor_required_keys():
    from skills.campaign.wizard import agent

    runs, _ = agent._divide(2000, _defaults())
    required = {"sender_key", "email", "from_name", "cc", "icp_label", "icp_desc",
               "template", "n_emails"}
    for r in runs:
        assert required <= set(r), f"missing keys: {required - set(r)}"
