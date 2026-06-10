"""Core module tests: atomic IO, schema validation edge cases, events."""

import os

import pytest

from toolbox.core import events, io, models


def test_csv_roundtrip_with_extras(tmp_path):
    rows = [
        models.Contact(email="A@X.com", first_name="A", hook="loves dogs"),
        models.Contact(email="b@y.io"),
    ]
    p = tmp_path / "c.csv"
    assert io.write_csv(p, rows) == 2
    back = io.read_csv(p, models.Contact)
    assert back[0].email == "a@x.com"  # canonicalized
    assert back[0].hook == "loves dogs"  # extra column survives


def test_csv_rejects_bad_email(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("email\nnot-an-email\n")
    with pytest.raises(io.ArtifactError, match="c.csv:2"):
        io.read_csv(p, models.Contact)


def test_csv_empty_file(tmp_path):
    p = tmp_path / "c.csv"
    assert io.write_csv(p, []) == 0
    assert io.read_csv(p, models.Contact) == []


def test_atomic_write_leaves_no_tmp(tmp_path):
    p = tmp_path / "x.csv"
    io.write_csv(p, [models.Domain(domain="https://www.Shop.COM/about")])
    assert not list(tmp_path.glob("*.tmp"))
    assert io.read_csv(p, models.Domain)[0].domain == "shop.com"  # canonicalized


def test_domain_rejects_garbage():
    with pytest.raises(ValueError):
        models.Domain(domain="notadomain")


def test_outbox_rejects_empty_subject():
    with pytest.raises(ValueError):
        models.OutboxRow(email="a@b.co", subject="  ", body="hi")


def test_jsonl_append_and_read(tmp_path):
    p = tmp_path / "l.jsonl"
    io.append_jsonl(p, {"a": 1})
    io.append_jsonl(p, {"b": 2})
    assert list(io.read_jsonl(p)) == [{"a": 1}, {"b": 2}]
    assert list(io.read_jsonl(tmp_path / "missing.jsonl")) == []


def test_events_to_run_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("TOOLBOX_RUN_ID", "r1")
    events.emit("step.completed", step_index=3)
    recs = events.read_all(tmp_path)
    assert recs[0]["event"] == "step.completed"
    assert recs[0]["run_id"] == "r1"
    assert recs[0]["step_index"] == 3


def test_events_without_run_dir_no_crash(monkeypatch, capsys):
    monkeypatch.delenv("TOOLBOX_RUN_DIR", raising=False)
    events.emit("loose.event")
    assert "loose.event" in capsys.readouterr().err
    assert not os.path.exists("events.jsonl")
