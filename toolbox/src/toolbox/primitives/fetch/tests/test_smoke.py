"""fetch offline smoke tests — HTTP mocked."""

import respx
from httpx import Response
from typer.testing import CliRunner

from toolbox.core import io
from toolbox.primitives.fetch.cli import app

runner = CliRunner()


@respx.mock
def test_urls_fetches_and_records_failures(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    respx.get("https://ok.example/page").mock(return_value=Response(200, text="hello world"))
    respx.get("https://down.example/x").mock(return_value=Response(404, text="nope"))
    src = tmp_path / "sources.csv"
    src.write_text("url\nhttps://ok.example/page\nhttps://down.example/x\n")
    out = tmp_path / "pages.jsonl"
    result = runner.invoke(app, ["urls", "--in", str(src), "--out", str(out)])
    assert result.exit_code == 0, result.output
    recs = {r["url"]: r for r in io.read_jsonl(out)}
    assert recs["https://ok.example/page"]["text"] == "hello world"
    assert recs["https://down.example/x"]["status"] == 404


@respx.mock
def test_urls_reddit_json_rewrite(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    route = respx.get("https://www.reddit.com/r/shopify/.json", params={"limit": "25"}).mock(
        return_value=Response(200, text="{}"))
    src = tmp_path / "sources.csv"
    src.write_text("url\nhttps://www.reddit.com/r/shopify\n")
    out = tmp_path / "pages.jsonl"
    result = runner.invoke(app, ["urls", "--in", str(src), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert route.called
