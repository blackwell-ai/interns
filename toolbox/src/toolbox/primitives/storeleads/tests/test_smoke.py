"""storeleads offline smoke tests."""

import respx
from httpx import Response
from typer.testing import CliRunner

from toolbox.core import io, models
from toolbox.primitives.storeleads.cli import API, app

runner = CliRunner()


@respx.mock
def test_search_dedupes_and_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_TOKEN_STORELEADS", "fake")
    respx.get(API).mock(return_value=Response(200, json={"domains": [
        {"name": "shopA.com", "title": "Shop A"},
        {"name": "shopa.com", "title": "Shop A dup"},
        {"name": "shopb.com", "merchant_name": "Shop B"},
    ]}))
    out = tmp_path / "domains.csv"
    result = runner.invoke(app, ["search", "--out", str(out), "--count", "10",
                                 "--segment", "yoga"])
    assert result.exit_code == 0, result.output
    rows = io.read_csv(out, models.Domain)
    assert [r.domain for r in rows] == ["shopa.com", "shopb.com"]
    assert rows[0].segment == "yoga"


@respx.mock
def test_search_empty_response(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_TOKEN_STORELEADS", "fake")
    respx.get(API).mock(return_value=Response(200, json={"domains": []}))
    out = tmp_path / "domains.csv"
    result = runner.invoke(app, ["search", "--out", str(out), "--count", "5"])
    assert result.exit_code == 0
    assert io.read_csv(out, models.Domain) == []
