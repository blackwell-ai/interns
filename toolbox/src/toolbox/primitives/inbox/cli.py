"""inbox primitive — file findings as inbox/queue/ tasks (repo task protocol).

Bridges any flow into the company's existing task queue: one markdown task per
record, using the inbox/TEMPLATE.md shape, addressed to a human by default.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime

import typer

from toolbox.core import config, events, io

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """inbox primitive."""


@app.command()
def file(
    in_: str = typer.Option(..., "--in", help="JSONL records (each becomes one task)"),
    title_field: str = typer.Option("summary", "--title-field"),
    assign_to: str = typer.Option("human", "--assign-to"),
    source: str = typer.Option("", "--source", help="who/what created these tasks (for provenance)"),
):
    records = list(io.read_jsonl(in_))
    queue = config.repo_root() / "inbox" / "queue"
    queue.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    filed = 0
    for rec in records:
        title = str(rec.get(title_field) or rec.get("reason") or rec.get("url") or "finding")[:80]
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "finding"
        path = queue / f"{today}-{slug}.md"
        n = 1
        while path.exists():
            n += 1
            path = queue / f"{today}-{slug}-{n}.md"
        body_lines = [f"- **{k}**: {str(v)[:500]}" for k, v in rec.items() if k != "text" and v]
        path.write_text(
            f"""---
title: "{title}"
created: {today}
created_by: {source or "automation-harness"}
assigned_to: {assign_to}
claimed_by:
claimed_at:
---

## Task

{rec.get("summary") or rec.get("reason") or title}

{chr(10).join(body_lines)}
""",
            encoding="utf-8",
        )
        events.emit("inbox.task_filed", path=str(path))
        filed += 1
    typer.echo(f"inbox.file: {filed} tasks filed")


if __name__ == "__main__":
    sys.exit(app())
