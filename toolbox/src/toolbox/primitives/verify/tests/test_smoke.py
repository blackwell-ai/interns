"""verify offline smoke tests — DNS stubbed at the cache boundary."""

from typer.testing import CliRunner

from toolbox.core import io, models
from toolbox.primitives.verify import cli

runner = CliRunner()


def test_check_drops_undeliverable(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setattr(cli, "_domain_has_mail",
                        lambda d, timeout=5.0: (d != "dead.com", "stub"))
    contacts = tmp_path / "c.csv"
    io.write_csv(contacts, [models.Contact(email="a@live.com"),
                            models.Contact(email="b@dead.com")])
    out = tmp_path / "v.csv"
    result = runner.invoke(cli.app, ["check", "--in", str(contacts), "--out", str(out)])
    assert result.exit_code == 0, result.output
    rows = io.read_csv(out, models.VerifiedContact)
    assert [r.email for r in rows] == ["a@live.com"]
    assert rows[0].verified and rows[0].mx_ok


def test_check_keep_unverified(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setattr(cli, "_domain_has_mail", lambda d, timeout=5.0: (False, "no MX, no A"))
    contacts = tmp_path / "c.csv"
    io.write_csv(contacts, [models.Contact(email="a@x.com")])
    out = tmp_path / "v.csv"
    result = runner.invoke(cli.app, ["check", "--in", str(contacts), "--out", str(out),
                                     "--keep-unverified"])
    assert result.exit_code == 0
    rows = io.read_csv(out, models.VerifiedContact)
    assert len(rows) == 1 and not rows[0].verified
    assert rows[0].verify_reason == "no MX, no A"


def test_check_empty_input(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    contacts = tmp_path / "c.csv"
    io.write_csv(contacts, [])
    out = tmp_path / "v.csv"
    result = runner.invoke(cli.app, ["check", "--in", str(contacts), "--out", str(out)])
    assert result.exit_code == 0
