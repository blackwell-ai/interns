"""Atomic, validated file I/O for run-folder artifacts.

Every write goes to `<name>.tmp` then `os.replace()` — rename is atomic on
POSIX, so a crash never leaves a half-written artifact that resume mistakes
for a complete one. A step's output existing is still NOT the "done" signal;
the runner trusts the `step.completed` event (core/events.py).
"""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

M = TypeVar("M", bound=BaseModel)


class ArtifactError(Exception):
    """A row failed schema validation — includes file and line for the report."""


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def read_csv(path: str | Path, model: type[M]) -> list[M]:
    path = Path(path)
    rows: list[M] = []
    with path.open(encoding="utf-8", newline="") as f:
        for i, raw in enumerate(csv.DictReader(f), start=2):
            try:
                rows.append(model.model_validate(raw))
            except ValidationError as e:
                raise ArtifactError(f"{path}:{i}: {e.errors()[0]['msg']} ({e.errors()[0]['loc']})") from e
    return rows


def write_csv(path: str | Path, rows: Iterable[BaseModel]) -> int:
    """Write models to CSV atomically. Column set = union of all row fields,
    declared fields first (stable order for diffing)."""
    path = Path(path)
    rows = list(rows)
    if not rows:
        _atomic_write_text(path, "")
        return 0
    declared = list(type(rows[0]).model_fields)
    extras: list[str] = []
    dumped = []
    for r in rows:
        d = r.model_dump()
        dumped.append(d)
        for k in d:
            if k not in declared and k not in extras:
                extras.append(k)
    fields = declared + extras
    import io as _io

    buf = _io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(dumped)
    _atomic_write_text(path, buf.getvalue())
    return len(rows)


def read_jsonl(path: str | Path) -> Iterator[dict]:
    path = Path(path)
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def append_jsonl(path: str | Path, record: dict) -> None:
    """Append one record, fsync'd. Append of a single small line is effectively
    atomic on POSIX; this is the local ledger-mirror primitive (build plan §7.1)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def write_json(path: str | Path, obj: object) -> None:
    _atomic_write_text(Path(path), json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
