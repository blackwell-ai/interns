"""compose offline smoke tests: rendering, frontmatter, drop-on-missing, names."""

import pytest
from typer.testing import CliRunner

from toolbox.core import io, models
from toolbox.primitives.compose import lib
from toolbox.primitives.compose.cli import app

runner = CliRunner()

TEMPLATE = """---
subject: Quick question about {{company}}
---
Hi {{first_name}},

{{hook}}

Best,
Me
"""


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    t = tmp_path / "template.md"
    t.write_text(TEMPLATE)
    contacts = tmp_path / "contacts.csv"
    io.write_csv(contacts, [
        models.Contact(email="a@x.com", name="Jane Doe", company="Xco", hook="saw your store"),
        models.Contact(email="b@y.com", name="Bob Roe", company="Yco", hook=""),  # empty slot
    ])
    return tmp_path, t, contacts


def test_render_and_drop_empty_slot(setup):
    tmp_path, template, contacts = setup
    out = tmp_path / "outbox.csv"
    result = runner.invoke(app, ["render", "--in", str(contacts), "--template", str(template),
                                 "--out", str(out)])
    assert result.exit_code == 0, result.output
    rows = io.read_csv(out, models.OutboxRow)
    assert len(rows) == 1  # Bob dropped: empty {{hook}}
    assert rows[0].subject == "Quick question about Xco"
    assert "Hi Jane," in rows[0].body
    assert "{{" not in rows[0].body


def test_on_missing_fail(setup):
    tmp_path, template, contacts = setup
    result = runner.invoke(app, ["render", "--in", str(contacts), "--template", str(template),
                                 "--out", str(tmp_path / "o.csv"), "--on-missing", "fail"])
    assert result.exit_code != 0


def test_template_requires_frontmatter():
    with pytest.raises(lib.TemplateError, match="frontmatter"):
        lib.parse_template("no frontmatter body")


def test_first_name_rules():
    assert lib.first_name("Dr. Jane Doe") == "Jane"
    assert lib.first_name("Robert Smith Jr.") == "Robert"  # ambiguous, no LLM → naive
    assert lib.first_name("Bob Roe") == "Bob"
    assert lib.is_ambiguous("Marie-Claire Dupont")
    assert lib.is_ambiguous("李伟 Wei")
    assert not lib.is_ambiguous("Jane Doe")
    # LLM fallback used only when ambiguous; failures fall back to naive
    assert lib.first_name("Marie-Claire Dupont", lambda n: "Marie-Claire") == "Marie-Claire"
    def boom(n):
        raise RuntimeError
    assert lib.first_name("Marie-Claire Dupont", boom) == "Marie-Claire"  # naive token


def test_render_empty_input(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLBOX_RUN_DIR", str(tmp_path))
    t = tmp_path / "t.md"
    t.write_text(TEMPLATE)
    empty = tmp_path / "contacts.csv"
    io.write_csv(empty, [])
    out = tmp_path / "outbox.csv"
    result = runner.invoke(app, ["render", "--in", str(empty), "--template", str(t),
                                 "--out", str(out)])
    assert result.exit_code == 0
    assert io.read_csv(out, models.OutboxRow) == []
