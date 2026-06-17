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


class _ItemVerdict(BaseModel):
    index: int
    relevant: bool
    reason: str = ""
    summary: str = ""


class _BatchVerdict(BaseModel):
    items: list[_ItemVerdict]


_BAR = (
    "Judge each item against the bar: {criteria!r}.\n"
    "Be strict: a summary of everything is noise. For an item that passes, give "
    "a 1-2 sentence summary of what matters."
)


@app.command("filter")
def filter_(
    in_: str = typer.Option(..., "--in", help="JSONL records"),
    out: str = typer.Option(..., "--out", help="JSONL of records that pass, + reason/summary"),
    criteria: str = typer.Option(..., "--criteria",
                                 help="plain-English bar, e.g. 'relevant to agentic commerce; a human would act on it'"),
    field: str = typer.Option("text", "--field", help="record field holding the content to judge"),
    model: str = typer.Option("", "--model"),
    batch: int = typer.Option(1, "--batch",
                              help="judge N items per LLM call (default 1). Use >1 for volume: "
                                   "170 items at --batch 25 is ~7 calls instead of 170."),
):
    from toolbox.core import llm

    if not Path(in_).exists():
        raise typer.BadParameter(f"input file not found: {in_}")
    records = [r for r in io.read_jsonl(in_) if str(r.get(field, "")).strip()]
    p = Path(out)
    if p.exists():
        p.unlink()

    def keep(rec: dict, reason: str, summary: str) -> None:
        io.append_jsonl(out, {**rec, "reason": reason, "summary": summary,
                              field: str(rec.get(field, ""))[:1000]})

    kept = 0
    if batch <= 1:
        for rec in records:
            content = str(rec.get(field, ""))[:8000]
            try:
                v = llm.parse(
                    _BAR.format(criteria=criteria) + "\n\nContent:\n" + content,
                    _Verdict, model=model or None,
                )
            except llm.LLMRefusal:
                continue
            if v.relevant:
                keep(rec, v.reason, v.summary)
                kept += 1
    else:
        # Batched: one structured call judges a chunk, returning a verdict per
        # index. Far fewer subprocess spawns, so it scales to a daily sweep.
        for start in range(0, len(records), batch):
            chunk = records[start:start + batch]
            listing = "\n\n".join(f"[{i}] {str(rec.get(field, ''))[:1500]}"
                                  for i, rec in enumerate(chunk))
            try:
                bv = llm.parse(
                    _BAR.format(criteria=criteria)
                    + "\nReturn a verdict for EVERY index below.\n\nItems:\n" + listing,
                    _BatchVerdict, model=model or None,
                )
            except llm.LLMRefusal:
                continue
            for v in bv.items:
                if 0 <= v.index < len(chunk) and v.relevant:
                    keep(chunk[v.index], v.reason, v.summary)
                    kept += 1
    events.emit("llm.filtered", total=len(records), kept=kept,
                criteria=criteria[:120], batch=batch)
    typer.echo(f"llm.filter: {kept}/{len(records)} passed")
    _ = json  # keep import explicit for future structured use


_DIGEST_SYSTEM = (
    "You are a research analyst writing an internal daily digest for a founding "
    "team working in and around agentic commerce, AI shopping, and e-commerce. "
    "Your job is to surface the problems people are running into and the notable "
    "developments in the space, so the team can brainstorm. The team is still "
    "exploring, so an interesting problem or development is worth surfacing on "
    "its own. Do NOT limit yourself to things adjacent to what the team has "
    "already built, and do NOT strain to connect items back to their work.\n"
    "Write like a sharp human teammate, not a content mill. Follow these hard "
    "rules: no em dashes or en dashes (use a plain hyphen, comma, or rewrite); "
    "sentence-case headings; no rule-of-three padding; no inflated significance; "
    "concrete claims tied to the specific post. Each bullet explains the problem "
    "the poster ran into, or the development itself, in plain terms, and never "
    "forces a connection to the team's own work. Cite where we found it: "
    "write `Source: <source> <url>` using the item's source and url exactly. An "
    "item from Hacker News is cited as 'Hacker News', a subreddit keeps its "
    "r/name; never rename the source to the website it links to. If a section "
    "has nothing real, write 'Nothing notable today.' Do not invent items "
    "beyond what you are given."
)

# Defensive humanizer sweep: the skill ships unattended, so strip the dash
# characters the system prompt forbids rather than trust the model every run.
_DASHES = {"—": ", ", "–": "-"}


def _sanitize(md: str) -> str:
    for bad, good in _DASHES.items():
        md = md.replace(bad, good)
    return md


def _sources_section(records: list[dict]) -> str:
    """A deterministic 'Sources indexed' list (source -> item count) so the
    digest shows the full coverage it swept, not only what cleared the bar."""
    from collections import Counter

    counts = Counter((str(r.get("source") or r.get("label") or "unknown")).strip() for r in records)
    if not counts:
        return ""
    lines = "\n".join(f"- {s} ({n})"
                      for s, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower())))
    return f"\n## Sources indexed\n{lines}\n"


@app.command()
def digest(
    in_: str = typer.Option(..., "--in", help="JSONL items that cleared the filter"),
    out: str = typer.Option("digest.md", "--out", help="markdown digest"),
    brain_dir: str = typer.Option("", "--brain-dir",
                                  help="if set, also write a dated copy here (YYYY-MM-DD.md)"),
    reviewed: int = typer.Option(0, "--reviewed", help="how many items were reviewed pre-filter"),
    reviewed_from: str = typer.Option("", "--reviewed-from",
                                      help="JSONL whose line count is the pre-filter reviewed total"),
    date: str = typer.Option("", "--date", help="digest date (default: today)"),
    model: str = typer.Option("", "--model"),
):
    """Synthesize a themed markdown digest from the items that cleared the bar."""
    from datetime import date as _date

    from toolbox.core import llm

    day = date or _date.today().isoformat()
    # Pre-filter items (everything indexed today) drive the reviewed count and
    # the "Sources indexed" coverage list. Fall back to the surfaced items.
    prefilter = list(io.read_jsonl(reviewed_from)) if reviewed_from else None
    if not reviewed:
        reviewed = len(prefilter) if prefilter is not None else 0
    items = list(io.read_jsonl(in_))
    # Keep the prompt compact: the fields that matter for synthesis.
    # Cite the source we found it on (source + url), not the link it points to,
    # so Hacker News and the subreddits are attributed, not the destination site.
    def _row(r):
        d = {"source": r.get("source") or r.get("label"), "title": r.get("title"),
             "why": r.get("reason") or r.get("summary"), "url": r.get("url")}
        # Papers (arXiv) carry their abstract so the digest can summarize the
        # paper itself, not just the filter's one-line relevance note.
        if r.get("kind") == "paper" or d["source"] == "arXiv":
            d["kind"] = "paper"
            d["abstract"] = (r.get("text") or "")[:600]
        return d

    compact = [_row(r) for r in items]

    if not compact:
        md = (f"# Researcher digest, {day}\n\n"
              f"Nothing cleared the relevance bar today"
              + (f" ({reviewed} items reviewed)." if reviewed else ".") + "\n")
    else:
        prompt = (
            f"Date: {day}. Items reviewed today: {reviewed or len(items)}; "
            f"{len(compact)} cleared the bar.\n\n"
            "Write the digest as markdown with this exact shape:\n"
            f"# Researcher digest, {day}\n"
            "<one or two plain sentences on the day's signal>\n\n"
            "## Problems and complaints\n"
            "## Ideas and opportunities\n"
            "## Competitor and market moves\n"
            "## Papers\n\n"
            "Each bullet: explain the problem the person hit or the development itself, "
            "in plain concrete terms (do not force a tie to the team's own work), then "
            "`Source: <source> <url>` taken verbatim from the item. Every bullet must "
            "end with that Source line. Put each item under the single best heading. "
            "Items with kind 'paper' are new research papers: put every one under "
            "## Papers and nowhere else, each formatted as `**Paper title** - a one to "
            "two sentence plain summary of what the paper does and why it is interesting`, "
            "then the `Source: arXiv <url>` line. Summarize from the item's abstract. "
            "End with a one-line `Reviewed N, surfaced M` footer.\n\n"
            "Items (JSON):\n" + json.dumps(compact, ensure_ascii=False)
        )
        md = llm.complete(prompt, system=_DIGEST_SYSTEM, model=model or None)

    md = _sanitize(md).strip() + "\n"
    md += _sources_section(prefilter if prefilter is not None else items)
    io.write_text(Path(out), md)
    wrote = [out]
    if brain_dir:
        brain_path = Path(brain_dir) / f"{day}.md"
        io.write_text(brain_path, md)
        wrote.append(str(brain_path))
    events.emit("llm.digest", items=len(compact), reviewed=reviewed, files=wrote)
    typer.echo(f"llm.digest: {len(compact)} items → {', '.join(wrote)}")


if __name__ == "__main__":
    sys.exit(app())
