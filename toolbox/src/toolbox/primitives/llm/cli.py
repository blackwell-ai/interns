"""llm primitive — generic LLM filter/transform over JSONL records.

The researcher's "filter hard" step (charter: 'would a human act on this or
want it in the brain?') as a reusable primitive: any flow can pass records +
criteria and get back the ones that clear the bar, each with a reason.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from pydantic import BaseModel

from toolbox.core import events, io

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """llm primitive."""


class _Verdict(BaseModel):
    relevant: bool
    reason: str
    summary: str = ""


@app.command("filter")
def filter_(
    in_: str = typer.Option(..., "--in", help="JSONL records"),
    out: str = typer.Option(..., "--out", help="JSONL of records that pass, + reason/summary"),
    criteria: str = typer.Option(..., "--criteria",
                                 help="plain-English bar, e.g. 'relevant to agentic commerce; a human would act on it'"),
    field: str = typer.Option("text", "--field", help="record field holding the content to judge"),
    model: str = typer.Option("", "--model"),
):
    from toolbox.core import llm

    if not Path(in_).exists():
        raise typer.BadParameter(f"input file not found: {in_}")
    records = list(io.read_jsonl(in_))
    p = Path(out)
    if p.exists():
        p.unlink()
    kept = 0
    for rec in records:
        content = str(rec.get(field, ""))[:8000]
        if not content.strip():
            continue
        try:
            v = llm.parse(
                f"Judge this content against the bar: {criteria!r}.\n"
                "Be strict — summaries of everything are noise. If it passes, give a 1-2 "
                "sentence summary of what matters.\n\nContent:\n" + content,
                _Verdict, model=model or None,
            )
        except llm.LLMRefusal:
            continue
        if v.relevant:
            io.append_jsonl(out, {**rec, "reason": v.reason, "summary": v.summary,
                                  field: content[:1000]})
            kept += 1
    events.emit("llm.filtered", total=len(records), kept=kept,
                criteria=criteria[:120])
    typer.echo(f"llm.filter: {kept}/{len(records)} passed")
    _ = json  # keep import explicit for future structured use


if __name__ == "__main__":
    sys.exit(app())
