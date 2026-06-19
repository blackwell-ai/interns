"""findemail offline smoke tests — HTTP mocked (respx), Apollo provider."""

import json

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from toolbox.core import io, models
from toolbox.primitives.findemail.cli import app

runner = CliRunner()

APOLLO_MATCH = "https://api.apollo.io/v1/people/match"
APOLLO_SEARCH = "https://api.apollo.io/v1/mixed_people/api_search"


@pytest.fixture
def candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_TOKEN_APOLLO", "fake")
    c = tmp_path / "cand.csv"
    c.write_text("brand,domain,name\nCaraway,carawayhome.com,Jordan Nathan\n"
                 "Cuts,cutsclothing.com,Steven Borrelli\n")
    return tmp_path, c


@respx.mock
def test_apollo_finds_and_keeps_passthrough(candidates):
    tmp_path, c = candidates
    respx.post(APOLLO_MATCH).mock(side_effect=[
        Response(200, json={"person": {"email": "jordan@carawayhome.com", "email_status": "verified"}}),
        Response(200, json={"person": {"email": "steven@cutsclothing.com", "email_status": "verified"}}),
    ])
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["find", "--in", str(c), "--out", str(out), "--concurrency", "1"])
    assert result.exit_code == 0, result.output
    rows = {r.email: r for r in io.read_csv(out, models.Contact)}
    assert rows["jordan@carawayhome.com"].first_name == "Jordan"
    assert rows["jordan@carawayhome.com"].brand == "Caraway"  # passthrough preserved
    assert int(rows["jordan@carawayhome.com"].email_score) == 95


@respx.mock
def test_apollo_drops_low_score_and_not_found(candidates):
    tmp_path, c = candidates
    respx.post(APOLLO_MATCH).mock(side_effect=[
        Response(200, json={"person": {"email": "jordan@carawayhome.com", "email_status": "guessed"}}),  # score 40, below min
        Response(200, json={"person": {"email": None, "email_status": "unavailable"}}),                  # not found
    ])
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["find", "--in", str(c), "--out", str(out),
                                 "--concurrency", "1", "--min-score", "80"])
    assert result.exit_code == 0, result.output
    assert io.read_csv(out, models.Contact) == []  # both dropped, neither guessed


@respx.mock
def test_find_exec_picks_decision_maker(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_TOKEN_APOLLO", "fake")
    domains = tmp_path / "domains.csv"
    domains.write_text("brand,domain\nCaraway,carawayhome.com\n")
    # api_search returns people without emails; the founder must outrank staff,
    # then the top pick is revealed via people/match.
    respx.post(APOLLO_SEARCH).mock(return_value=Response(200, json={"people": [
        {"id": "p_support", "first_name": "Sam", "title": "Support Agent"},
        {"id": "p_founder", "first_name": "Jordan", "title": "Founder & CEO"},
    ]}))
    respx.post(APOLLO_MATCH).mock(return_value=Response(200, json={"person": {
        "email": "jordan@carawayhome.com", "first_name": "Jordan", "last_name": "Nathan",
        "title": "Founder & CEO", "email_status": "verified"}}))
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["find-exec", "--in", str(domains), "--out", str(out)])
    assert result.exit_code == 0, result.output
    rows = io.read_csv(out, models.Contact)
    assert len(rows) == 1
    assert rows[0].email == "jordan@carawayhome.com"  # founder, not the support agent
    assert rows[0].first_name == "Jordan"
    assert rows[0].brand == "Caraway"


@respx.mock
def test_find_exec_cache_skips_apollo(tmp_path, monkeypatch):
    """A domain already in the cache is never re-queried (0 extra Apollo calls)."""
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_TOKEN_APOLLO", "fake")
    domains = tmp_path / "domains.csv"
    domains.write_text("brand,domain\nCaraway,carawayhome.com\nNew,newbrand.com\n")
    cache = tmp_path / "cache.jsonl"
    # carawayhome is pre-cached; newbrand is not
    cache.write_text('{"domain":"carawayhome.com","email":"jordan@carawayhome.com",'
                     '"first_name":"Jordan","last_name":"Nathan","title":"CEO",'
                     '"email_score":97,"email_status":"verified"}\n')
    route = respx.post(APOLLO_SEARCH).mock(return_value=Response(200, json={"people": [
        {"id": "p_ann", "first_name": "Ann", "title": "Founder"}]}))
    respx.post(APOLLO_MATCH).mock(return_value=Response(200, json={"person": {
        "email": "ceo@newbrand.com", "first_name": "Ann", "last_name": "Doe",
        "title": "Founder", "email_status": "verified"}}))
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["find-exec", "--in", str(domains), "--out", str(out),
                                 "--cache", str(cache)])
    assert result.exit_code == 0, result.output
    assert route.call_count == 1          # only newbrand hit Apollo; caraway came from cache
    emails = {r.email for r in io.read_csv(out, models.Contact)}
    assert emails == {"jordan@carawayhome.com", "ceo@newbrand.com"}
    # newbrand is now appended to the cache for next time
    assert "newbrand.com" in cache.read_text()


@respx.mock
def test_find_exec_thorough_uses_limit_25(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_TOKEN_APOLLO", "fake")
    domains = tmp_path / "domains.csv"
    domains.write_text("brand,domain\nX,x.com\n")
    captured = {}
    def handler(req):
        captured["body"] = json.loads(req.content)
        return Response(200, json={"people": [{"id": "p_f", "first_name": "F", "title": "Founder"}]})
    respx.post(APOLLO_SEARCH).mock(side_effect=handler)
    respx.post(APOLLO_MATCH).mock(return_value=Response(200, json={"person": {
        "email": "f@x.com", "first_name": "F", "last_name": "X", "title": "Founder",
        "email_status": "verified"}}))
    out = tmp_path / "c.csv"
    runner.invoke(app, ["find-exec", "--in", str(domains), "--out", str(out), "--thorough"])
    assert captured["body"]["per_page"] == 25
    assert "person_seniorities" not in captured["body"]  # thorough = no seniority filter


@respx.mock
def test_apollo_retries_429(candidates):
    tmp_path, c = candidates
    route = respx.post(APOLLO_MATCH)
    route.side_effect = [
        Response(429, json={"error": "slow down"}),
        Response(200, json={"person": {"email": "jordan@carawayhome.com", "email_status": "verified"}}),
        Response(200, json={"person": {"email": "steven@cutsclothing.com", "email_status": "verified"}}),
    ]
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["find", "--in", str(c), "--out", str(out), "--concurrency", "1"])
    assert result.exit_code == 0, result.output
    assert len(io.read_csv(out, models.Contact)) == 2  # backoff recovered
