"""domains offline smoke tests — LLM stubbed (no network, no API key)."""

from typer.testing import CliRunner

from toolbox.core import io, llm, models
from toolbox.primitives.domains.cli import _Found, _Queries, app

runner = CliRunner()


def test_source_dedupes_and_canonicalizes(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))

    def fake_parse(prompt, schema, **kw):
        if schema is _Queries:
            return _Queries(queries=["q1", "q2"])
        return _Found(retailers=[
            _Found.Item(company_name="A", domain="https://www.a-shop.com/about", source_url="s"),
            _Found.Item(company_name="A2", domain="a-shop.com", source_url="s"),  # dup
            _Found.Item(company_name="bad", domain="not a domain", source_url=""),
        ])

    monkeypatch.setattr(llm, "parse", fake_parse)
    monkeypatch.setattr(llm, "web_search", lambda *a, **k: "research text")

    out = tmp_path / "domains.csv"
    result = runner.invoke(app, ["source", "--query", "yoga stores", "--count", "50",
                                 "--out", str(out)])
    assert result.exit_code == 0, result.output
    rows = io.read_csv(out, models.Domain)
    assert [r.domain for r in rows] == ["a-shop.com"]  # canonical + dedup + garbage dropped
    assert rows[0].segment == "yoga stores"
