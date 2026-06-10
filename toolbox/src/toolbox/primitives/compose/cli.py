"""compose primitive — fill a template per contact, optionally LLM-personalize."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from toolbox.core import events, io, models
from toolbox.primitives.compose import lib

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """compose primitive."""


@app.command()
def render(
    in_: str = typer.Option(..., "--in", help="contacts CSV (any columns; rows feed the slots)"),
    template: str = typer.Option(..., "--template", help="template file with subject frontmatter"),
    out: str = typer.Option(..., "--out"),
    personalize: bool = typer.Option(False, "--personalize",
                                     help="LLM-fill a {{personalization_hook}} slot per row"),
    model: str = typer.Option("", "--model", help="override the LLM model for personalization"),
    on_missing: str = typer.Option("drop", "--on-missing", help="drop | fail (a row with an empty slot)"),
):
    """contacts.csv + template -> outbox.csv (email, subject, body, …)."""
    rows = io.read_csv(in_, models.Contact)
    subject_t, body_t = lib.parse_template(Path(template).read_text(encoding="utf-8"))
    needs_hook = "personalization_hook" in (lib.find_slots(subject_t) | lib.find_slots(body_t))

    llm_first = _llm_first_name(model) if personalize else None
    out_rows: list[models.OutboxRow] = []
    dropped = 0
    for row in rows:
        values = row.model_dump()
        if not values.get("first_name"):
            source = values.get("name") or values.get("first_name") or ""
            if source:
                values["first_name"] = lib.first_name(source, llm_first)
        if needs_hook and not values.get("personalization_hook"):
            if personalize:
                values["personalization_hook"] = _hook(values, model)
            # else: leave empty → render() raises → drop/fail below (this is
            # exactly the bug the dry-run catches in the spec's worked example)
        try:
            out_rows.append(models.OutboxRow(
                email=row.email,
                subject=lib.render(subject_t, values),
                body=lib.render(body_t, values),
                **{k: v for k, v in values.items()
                   if k not in ("email", "subject", "body") and isinstance(v, str | int | float | bool)},
            ))
        except lib.TemplateError as e:
            if on_missing == "fail":
                raise
            dropped += 1
            events.emit("compose.row_dropped", level="warn", email=row.email, reason=str(e))
    n = io.write_csv(out, out_rows)
    events.emit("compose.rendered", count=n, dropped=dropped)
    typer.echo(f"compose.render: {n} rendered, {dropped} dropped")


def _llm_first_name(model: str):
    def fallback(name: str) -> str:
        from pydantic import BaseModel

        from toolbox.core import llm

        class FirstName(BaseModel):
            first_name: str

        return llm.parse(
            "Given a full personal name, return the form the person would prefer in an "
            "English salutation. 'Marie-Claire Dupont' -> 'Marie-Claire'; '李伟' -> 'Wei'; "
            f"'Robert Smith Jr.' -> 'Robert'. Name: {name}",
            FirstName, model=model or None,
        ).first_name

    return fallback


def _hook(values: dict, model: str) -> str:
    from pydantic import BaseModel

    from toolbox.core import llm

    class Hook(BaseModel):
        hook: str

    context = json.dumps({k: v for k, v in values.items() if v and isinstance(v, str)})[:1500]
    try:
        return llm.parse(
            "Write ONE short, specific, non-flattering opening line for a cold email to this "
            "person, grounded in a real fact from the data below (their store, role, company). "
            "No generic praise. Under 25 words. If the data has nothing concrete, return an "
            "empty hook.\n\n" + context,
            Hook, model=model or None,
        ).hook
    except Exception as e:
        events.emit("compose.hook_failed", level="warn", reason=str(e)[:200])
        return ""


if __name__ == "__main__":
    sys.exit(app())
