from typer.testing import CliRunner

from toolbox.primitives.throttle.cli import app

runner = CliRunner()


def test_wait(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    result = runner.invoke(app, ["wait", "--seconds", "0.01"])
    assert result.exit_code == 0
