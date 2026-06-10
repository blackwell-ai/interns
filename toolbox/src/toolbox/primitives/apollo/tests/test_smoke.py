"""apollo offline smoke tests — HTTP mocked, incl. 429-then-success backoff."""

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from toolbox.core import io, models
from toolbox.primitives.apollo.cli import APOLLO_API, app

runner = CliRunner()


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_TOKEN_APOLLO", "fake-key")
    domains = tmp_path / "domains.csv"
    io.write_csv(domains, [models.Domain(domain="x.com", company="Xco")])
    return tmp_path, domains


PERSON = {"email": "jane@x.com", "first_name": "Jane", "last_name": "Doe",
          "name": "Jane Doe", "title": "CEO", "organization": {"name": "Xco"}}


@respx.mock
def test_enrich_happy_path(setup):
    tmp_path, domains = setup
    respx.post(f"{APOLLO_API}/mixed_people/search").mock(
        return_value=Response(200, json={"people": [PERSON]}))
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["enrich", "--in", str(domains), "--out", str(out)])
    assert result.exit_code == 0, result.output
    rows = io.read_csv(out, models.Contact)
    assert rows[0].email == "jane@x.com" and rows[0].title == "CEO"


@respx.mock
def test_enrich_filters_locked_and_invalid_emails(setup):
    tmp_path, domains = setup
    people = [dict(PERSON, email="email_not_unlocked@domain.com"),
              dict(PERSON, email=""), dict(PERSON, email=None)]
    respx.post(f"{APOLLO_API}/mixed_people/search").mock(
        return_value=Response(200, json={"people": people}))
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["enrich", "--in", str(domains), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert io.read_csv(out, models.Contact) == []


@respx.mock
def test_enrich_retries_429_then_succeeds(setup):
    tmp_path, domains = setup
    route = respx.post(f"{APOLLO_API}/mixed_people/search")
    route.side_effect = [Response(429, text="slow down"),
                         Response(200, json={"people": [PERSON]})]
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["enrich", "--in", str(domains), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert route.call_count == 2  # backoff retried, didn't crash
    assert len(io.read_csv(out, models.Contact)) == 1


@respx.mock
def test_enrich_zero_results(setup):
    tmp_path, domains = setup
    respx.post(f"{APOLLO_API}/mixed_people/search").mock(
        return_value=Response(200, json={"people": []}))
    out = tmp_path / "contacts.csv"
    result = runner.invoke(app, ["enrich", "--in", str(domains), "--out", str(out)])
    assert result.exit_code == 0
    assert io.read_csv(out, models.Contact) == []
