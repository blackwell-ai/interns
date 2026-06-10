"""inbox.file offline smoke tests — files tasks into a fake repo."""

from typer.testing import CliRunner

from toolbox.core import io
from toolbox.primitives.inbox.cli import app

runner = CliRunner()


def test_files_tasks_with_template_shape(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()  # repo_root() marker
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "filtered.jsonl"
    io.append_jsonl(src, {"url": "https://x", "summary": "Competitor launched agent checkout",
                          "reason": "directly relevant"})
    io.append_jsonl(src, {"url": "https://y", "summary": "Competitor launched agent checkout"})
    result = runner.invoke(app, ["file", "--in", str(src), "--source", "researcher-agent"])
    assert result.exit_code == 0, result.output
    tasks = sorted((tmp_path / "inbox" / "queue").glob("*.md"))
    assert len(tasks) == 2  # name collision got a -2 suffix
    text = tasks[0].read_text()
    assert "assigned_to: human" in text
    assert "created_by: researcher-agent" in text
    assert "Competitor launched agent checkout" in text
