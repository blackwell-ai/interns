"""Structured events to runs/<id>/events.jsonl (port of observability.py).

Primitives discover the run folder via TOOLBOX_RUN_DIR (set by the runner) so
they need no extra flags. Outside a run (ad-hoc CLI use) events go to stderr.

The `step.completed` event is the authoritative "this step is done" signal for
resume — artifact existence alone is not (see core/io.py).
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

from toolbox.core import io


def _run_dir() -> str | None:
    return os.environ.get("TOOLBOX_RUN_DIR")


def emit(event: str, level: str = "info", **fields: object) -> dict:
    record: dict = {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "run_id": os.environ.get("TOOLBOX_RUN_ID", ""),
        "event": event,
        "level": level,
        **fields,
    }
    run_dir = _run_dir()
    if run_dir:
        io.append_jsonl(os.path.join(run_dir, "events.jsonl"), record)
    else:
        print(f"[{record['ts']}] {event} {fields}", file=sys.stderr)
    return record


def read_all(run_dir: str | os.PathLike) -> list[dict]:
    return list(io.read_jsonl(os.path.join(os.fspath(run_dir), "events.jsonl")))
