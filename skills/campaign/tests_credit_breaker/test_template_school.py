"""Offline tests for per-sender school adaptation, the sample renderer, and
free-text ICP pass-through. No LLM, no network. Delete this folder after merge.

    cd /Users/shamitd/interns/toolbox
    uv run python -m pytest ../skills/campaign/tests_credit_breaker/ -v
"""
from __future__ import annotations


# ---- school mapping ----------------------------------------------------

def test_school_for_email_maps_each_sender():
    from skills.campaign.wizard import agent

    assert agent.school_for_email("armaan.priyadarshan.29@dartmouth.edu") == ("Dartmouth", "Stanford/Berkeley")
    assert agent.school_for_email("samarjit.deshmukh.29@dartmouth.edu") == ("Dartmouth", "Stanford/Berkeley")
    assert agent.school_for_email("ethanpzhou@berkeley.edu") == ("Berkeley", "Stanford/Dartmouth")
    # unknown domain falls back to Stanford
    assert agent.school_for_email("someone@gmail.com") == ("Stanford", "Dartmouth/Berkeley")


def test_run_and_agent_school_helpers_agree():
    """The server-side helper (for preview) and run.py's (for the real send)
    must produce identical text, or the preview would lie about the send."""
    from skills.campaign.wizard import agent
    from skills.campaign import run as camp

    for email in ("armaan.priyadarshan.29@dartmouth.edu", "ethanpzhou@berkeley.edu",
                  "x@stanford.edu", "y@unknown.org"):
        assert agent.school_for_email(email) == camp.school_for_email(email)


# ---- the core fix: each sender's sample uses its own school -------------

def test_sample_uses_senders_real_school():
    from skills.campaign.wizard import agent

    dartmouth_run = {"email": "armaan.priyadarshan.29@dartmouth.edu",
                     "from_name": "Armaan", "template": agent.DEFAULT_TEMPLATE}
    berkeley_run = {"email": "ethanpzhou@berkeley.edu",
                    "from_name": "Ethan", "template": agent.DEFAULT_TEMPLATE}

    _, dart_body = agent.render_sample(dartmouth_run)
    _, berk_body = agent.render_sample(berkeley_run)

    # Armaan's email says Dartmouth (and names the other two), never claims Berkeley as his.
    assert "student at Dartmouth" in dart_body
    assert "Stanford/Berkeley" in dart_body
    # Ethan's email says Berkeley — the bug this whole change fixes.
    assert "student at Berkeley" in berk_body
    assert "Stanford/Dartmouth" in berk_body
    # No raw template slots left unrendered.
    assert "{{" not in dart_body and "{{" not in berk_body


def test_sample_subject_stays_stanford_for_all():
    """Per the chosen policy, the subject does NOT adapt to the sender's school."""
    from skills.campaign.wizard import agent

    subj, _ = agent.render_sample({"email": "ethanpzhou@berkeley.edu",
                                   "from_name": "Ethan", "template": agent.DEFAULT_TEMPLATE})
    assert "Stanford" in subj


# ---- free-text ICP pass-through ---------------------------------------

def test_freetext_icp_passes_through_with_brand_template():
    from skills.campaign.wizard import agent

    runs, deferred = agent._divide(
        50, [{"label": "neo labs", "icp": "neobanking infrastructure startups", "weight": 1.0}])
    assert deferred == 0
    assert sum(r["n_emails"] for r in runs) == 50
    assert {r["icp_label"] for r in runs} == {"neo labs"}            # kept verbatim
    assert {r["icp_desc"] for r in runs} == {"neobanking infrastructure startups"}
    assert {r["template"] for r in runs} == {agent.DEFAULT_TEMPLATE}  # brand template for all


def test_all_runs_use_brand_template_by_default():
    from skills.campaign.wizard import agent

    runs, _ = agent._divide(2000, [
        {"label": "DTC brands", "icp": "DTC brands", "weight": 0.6},
        {"label": "aerospace manufacturers", "icp": "aerospace manufacturers", "weight": 0.4},
    ])
    assert {r["template"] for r in runs} == {agent.DEFAULT_TEMPLATE}
