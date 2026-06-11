"""findemail offline smoke tests — HTTP mocked (respx), both providers."""

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from toolbox.core import io, models
from toolbox.primitives.findemail.cli import app

runner = CliRunner()

HUNTER = "https://api.hunter.io/v2/email-finder"
HUNTER_DOMAIN = "https://api.hunter.io/v2/domain-search"
FINDYMAIL = "https://app.findymail.com/api/search/name"


@pytest.fixture
def candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_TOKEN_HUNTER", "fake")
    monkeypatch.setenv("TOOLBOX_TOKEN_FINDYMAIL", "fake")
    c = tmp_path / "cand.csv"
    c.write_text("brand,domain,name\nCaraway,carawayhome.com,Jordan Nathan\n"
                 "Cuts,cutsclothing.com,Steven Borrelli\n")
    return tmp_path, c


@respx.mock
def test_hunter_finds_and_keeps_passthrough(candidates):
    tmp_path, c = candidates
    respx.get(HUNTER).mock(side_effect=[
        Response(200, json={"data": {"email": "jordan@carawayhome.com", "score": 95,
                                     "verification": {"status": "valid"}}}),
        Response(200, json={"data": {"email": "steven@cutsclothing.com", "score": 88,
                                     "verification": {"status": "valid"}}}),
    ])
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["find", "--in", str(c), "--out", str(out), "--concurrency", "1"])
    assert result.exit_code == 0, result.output
    rows = {r.email: r for r in io.read_csv(out, models.Contact)}
    assert rows["jordan@carawayhome.com"].first_name == "Jordan"
    assert rows["jordan@carawayhome.com"].brand == "Caraway"  # passthrough preserved
    assert int(rows["jordan@carawayhome.com"].email_score) == 95


@respx.mock
def test_hunter_drops_low_score_and_not_found(candidates):
    tmp_path, c = candidates
    respx.get(HUNTER).mock(side_effect=[
        Response(200, json={"data": {"email": "jordan@carawayhome.com", "score": 50,
                                     "verification": {"status": "unknown"}}}),  # below min
        Response(200, json={"data": {"email": None, "score": 0}}),             # not found
    ])
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["find", "--in", str(c), "--out", str(out),
                                 "--concurrency", "1", "--min-score", "80"])
    assert result.exit_code == 0, result.output
    assert io.read_csv(out, models.Contact) == []  # both dropped, neither guessed


@respx.mock
def test_findymail_provider(candidates):
    tmp_path, c = candidates
    respx.post(FINDYMAIL).mock(side_effect=[
        Response(200, json={"contact": {"email": "jordan@carawayhome.com"}}),
        Response(200, json={"contact": {"email": "steven@cutsclothing.com"}}),
    ])
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["find", "--in", str(c), "--out", str(out),
                                 "--provider", "findymail", "--concurrency", "1"])
    assert result.exit_code == 0, result.output
    assert len(io.read_csv(out, models.Contact)) == 2


@respx.mock
def test_find_exec_picks_decision_maker(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_TOKEN_HUNTER", "fake")
    domains = tmp_path / "domains.csv"
    domains.write_text("brand,domain\nCaraway,carawayhome.com\n")
    # domain search returns several people; the founder must be chosen over staff
    respx.get(HUNTER_DOMAIN).mock(return_value=Response(200, json={"data": {"emails": [
        {"value": "support@carawayhome.com", "first_name": "Sam", "last_name": "Help",
         "position": "Support Agent", "seniority": "junior", "confidence": 99},
        {"value": "jordan@carawayhome.com", "first_name": "Jordan", "last_name": "Nathan",
         "position": "Founder & CEO", "seniority": "executive", "confidence": 92,
         "verification": {"status": "valid"}},
    ]}}))
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["find-exec", "--in", str(domains), "--out", str(out)])
    assert result.exit_code == 0, result.output
    rows = io.read_csv(out, models.Contact)
    assert len(rows) == 1
    assert rows[0].email == "jordan@carawayhome.com"  # founder, not the higher-confidence support
    assert rows[0].first_name == "Jordan"
    assert rows[0].brand == "Caraway"


@respx.mock
def test_hunter_retries_429(candidates):
    tmp_path, c = candidates
    route = respx.get(HUNTER)
    route.side_effect = [
        Response(429, json={"errors": [{"details": "slow down"}]}),
        Response(200, json={"data": {"email": "jordan@carawayhome.com", "score": 95,
                                     "verification": {"status": "valid"}}}),
        Response(200, json={"data": {"email": "steven@cutsclothing.com", "score": 90,
                                     "verification": {"status": "valid"}}}),
    ]
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["find", "--in", str(c), "--out", str(out), "--concurrency", "1"])
    assert result.exit_code == 0, result.output
    assert len(io.read_csv(out, models.Contact)) == 2  # backoff recovered
