"""llm.filter offline smoke tests — model stubbed."""

from typer.testing import CliRunner

from toolbox.core import io
from toolbox.core import llm as core_llm
from toolbox.primitives.llm.cli import _Verdict, app

runner = CliRunner()


def test_filter_keeps_relevant_only(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))

    def fake_parse(prompt, schema, **kw):
        # key on the record CONTENT, not the criteria (which is in every prompt)
        relevant = "eating the world" in prompt
        return _Verdict(relevant=relevant, reason="r", summary="s")

    monkeypatch.setattr(core_llm, "parse", fake_parse)
    src = tmp_path / "pages.jsonl"
    io.append_jsonl(src, {"url": "u1", "text": "agentic commerce is eating the world"})
    io.append_jsonl(src, {"url": "u2", "text": "cat pictures"})
    io.append_jsonl(src, {"url": "u3", "text": ""})  # empty content skipped
    out = tmp_path / "filtered.jsonl"
    result = runner.invoke(app, ["filter", "--in", str(src), "--out", str(out),
                                 "--criteria", "relevant to agentic commerce"])
    assert result.exit_code == 0, result.output
    recs = list(io.read_jsonl(out))
    assert len(recs) == 1 and recs[0]["url"] == "u1" and recs[0]["summary"] == "s"
