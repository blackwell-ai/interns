"""Process primitives (spec §5) — the steps that used to be a hardcoded
"build loop", now optional lines in a flow. Each is removable; none is law.

Pause protocol: clarify-ask and canary-run exit PAUSE_EXIT_CODE (75) when they
need a human; they leave a marker file so that on `toolbox resume` the re-run
of the same step sees the marker and completes instead of pausing again.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import typer
from ruamel.yaml import YAML

from toolbox.core import config, events, io

app = typer.Typer(no_args_is_help=True)
yaml = YAML()


@app.callback()
def _group():
    """process primitives."""


def _ctx() -> tuple[Path, Path, str, str]:
    run_dir = Path(os.environ.get("TOOLBOX_RUN_DIR", "."))
    skill_dir = Path(os.environ.get("TOOLBOX_SKILL_DIR", "."))
    return run_dir, skill_dir, os.environ.get("TOOLBOX_RUN_ID", ""), os.environ.get("TOOLBOX_SKILL", "")


def _flow_steps(run_dir: Path) -> list:
    with (run_dir / "flow.resolved.yaml").open() as f:
        return list((yaml.load(f) or {}).get("steps") or [])


def _find_step(steps: list, name: str) -> dict:
    for s in steps:
        if isinstance(s, dict) and len(s) == 1 and next(iter(s)) == name:
            return dict(next(iter(s.values())) or {})
    raise typer.BadParameter(f"flow has no step named {name!r}")


# ---- plan.write --------------------------------------------------------------


@app.command("plan-write")
def plan_write():
    """Draft SKILL.md from flow.yaml + inputs.yaml if it doesn't exist yet."""
    run_dir, skill_dir, _, skill = _ctx()
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        events.emit("plan.exists", path=str(skill_md))
        return
    inputs = {}
    if (skill_dir / "inputs.yaml").exists():
        with (skill_dir / "inputs.yaml").open() as f:
            inputs = dict(yaml.load(f) or {})
    steps = []
    if (skill_dir / "flow.yaml").exists():
        with (skill_dir / "flow.yaml").open() as f:
            steps = list((yaml.load(f) or {}).get("steps") or [])
    step_lines = "\n".join(
        f"- `{next(iter(s)) if isinstance(s, dict) else s}`" for s in steps
    )
    input_lines = "\n".join(f"- `{k}` (default: `{v}`)" for k, v in inputs.items())
    skill_md.write_text(
        f"""# {skill}

<!-- Drafted by plan.write — refine the Purpose and Acceptance checks before first live run. -->

## Purpose

TODO: one paragraph on what this skill does and when to use it.

## Inputs

{input_lines or "- (none)"}

## Steps

{step_lines or "- (none)"}

## Acceptance checks

- Every rendered message has a non-empty subject and body.
- No unresolved {{{{slot}}}} placeholders survive rendering.

## Changelog
""",
        encoding="utf-8",
    )
    events.emit("plan.written", path=str(skill_md))
    typer.echo(f"plan.write: drafted {skill_md}")


# ---- clarify.ask ---------------------------------------------------------------


@app.command("clarify-ask")
def clarify_ask():
    """ONE review pass over the run's inputs.yaml (every field pre-filled).

    TTY: prompt inline. Headless: pause (75) so a human can edit
    runs/<id>/inputs.yaml and `toolbox resume`. TOOLBOX_ASSUME_YES skips it.
    """
    run_dir, _, _, _ = _ctx()
    marker = run_dir / ".clarify.confirmed"
    inputs_path = run_dir / "inputs.yaml"

    if os.environ.get("TOOLBOX_ASSUME_YES") or marker.exists():
        marker.write_text(datetime.now(UTC).isoformat())
        events.emit("clarify.accepted", interactive=False)
        typer.echo("clarify.ask: inputs accepted")
        return

    with inputs_path.open() as f:
        inputs = dict(yaml.load(f) or {})

    if sys.stdin.isatty():
        typer.echo("Review inputs (Enter keeps the default):")
        for k, v in inputs.items():
            new = typer.prompt(f"  {k}", default=str(v))
            inputs[k] = new
        with inputs_path.open("w") as f:
            yaml.dump(inputs, f)
        marker.write_text(datetime.now(UTC).isoformat())
        events.emit("clarify.accepted", interactive=True)
        typer.echo("clarify.ask: inputs confirmed")
        return

    # Headless: pause for human edit.
    marker.write_text(datetime.now(UTC).isoformat())  # next run of this step accepts
    typer.echo(f"clarify.ask: review/edit {inputs_path} then resume", err=True)
    events.emit("clarify.pending")
    raise typer.Exit(config.PAUSE_EXIT_CODE)


# ---- test.smoke -----------------------------------------------------------------


@app.command("test-smoke")
def test_smoke():
    """Run the offline smoke tests of every primitive this flow uses."""
    run_dir, _, _, _ = _ctx()
    used: set[str] = set()
    for s in _flow_steps(run_dir):
        name = next(iter(s)) if isinstance(s, dict) else str(s)
        prefix = name.split(".", 1)[0]
        if prefix not in ("plan", "clarify", "test", "canary", "report", "python"):
            used.add(prefix)
    import toolbox.primitives as prims

    base = Path(prims.__file__).parent
    targets = [str(base / u / "tests") for u in sorted(used) if (base / u / "tests").exists()]
    if not targets:
        events.emit("smoke.no_tests", primitives=sorted(used))
        typer.echo("test.smoke: no test folders found for used primitives", err=True)
        raise typer.Exit(1)
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-m", "not integration", *targets])
    events.emit("smoke.finished", primitives=sorted(used), exit_code=proc.returncode)
    if proc.returncode != 0:
        raise typer.Exit(proc.returncode)
    typer.echo(f"test.smoke: green for {', '.join(sorted(used))}")


# ---- test.dryrun -----------------------------------------------------------------


@app.command("test-dryrun")
def test_dryrun(
    of: str = typer.Option(..., "--of", help="the send-class step to dry-run, e.g. gmail.send"),
    sample: int = typer.Option(10, "--sample"),
    checks: str = typer.Option("", "--checks", help="SKILL.md#acceptance-checks (informational)"),
):
    """Execute the send-class step with --dry-run on a sample; grade the output."""
    run_dir, _, _, _ = _ctx()
    args = _find_step(_flow_steps(run_dir), of)

    src = run_dir / str(args.get("in", ""))
    sample_file = run_dir / "dryrun.sample.csv"
    lines = src.read_text(encoding="utf-8").splitlines()
    sample_file.write_text("\n".join(lines[: sample + 1]) + "\n", encoding="utf-8")

    module = f"toolbox.primitives.{of.split('.', 1)[0]}.cli"
    command = of.split(".", 1)[1]
    argv = [sys.executable, "-m", module, command, "--dry-run", "--in", str(sample_file)]
    for k, v in args.items():
        if k == "in":
            continue
        flag = "--" + str(k).replace("_", "-")
        if isinstance(v, bool):
            if v:
                argv.append(flag)
        else:
            argv += [flag, str(v)]
    proc = subprocess.run(argv, cwd=run_dir)
    if proc.returncode != 0:
        raise typer.Exit(proc.returncode)

    # Grade: deterministic checks on what WOULD have been sent.
    out = run_dir / "dryrun" / f"{of}.json"
    problems: list[str] = []
    if out.exists():
        for i, rec in enumerate(io.read_json(out)):
            for field in ("subject", "body"):
                value = str(rec.get(field, ""))
                if not value.strip():
                    problems.append(f"row {i}: empty {field}")
                if "{{" in value:
                    problems.append(f"row {i}: unresolved placeholder in {field}: {value[:80]}")
    else:
        problems.append(f"dry-run produced no {out.name}")
    events.emit("dryrun.graded", sample=sample, problems=problems, checks=checks)
    if problems:
        typer.echo("test.dryrun FAILED:\n  " + "\n  ".join(problems), err=True)
        raise typer.Exit(1)
    typer.echo(f"test.dryrun: {sample}-row sample looks good")


# ---- canary.run -------------------------------------------------------------------


@app.command("canary-run")
def canary_run(
    of: str = typer.Option(..., "--of"),
    count: int = typer.Option(10, "--count"),
    seeds: str = typer.Option("", "--seeds", help="comma-separated seed inboxes (ours)"),
):
    """Small LIVE batch (count real recipients + seeds), then a human go/no-go gate."""
    run_dir, _, run_id, _ = _ctx()
    marker = run_dir / ".canary.approved"
    if marker.exists() or os.environ.get("TOOLBOX_ASSUME_YES"):
        events.emit("canary.approved")
        typer.echo("canary.run: approved")
        return

    args = _find_step(_flow_steps(run_dir), of)
    module = f"toolbox.primitives.{of.split('.', 1)[0]}.cli"
    command = of.split(".", 1)[1]

    def run_send(extra: list[str], in_file: str) -> None:
        argv = [sys.executable, "-m", module, command, "--in", in_file, *extra]
        for k, v in args.items():
            if k in ("in", "limit"):
                continue
            flag = "--" + str(k).replace("_", "-")
            if isinstance(v, bool):
                if v:
                    argv.append(flag)
            else:
                argv += [flag, str(v)]
        proc = subprocess.run(argv, cwd=run_dir)
        if proc.returncode != 0:
            raise typer.Exit(proc.returncode)

    # 1) first `count` real recipients (real sends; the ledger remembers them,
    #    so the full send later naturally skips them — no double contact).
    run_send(["--limit", str(count)], str(args.get("in", "")))

    # 2) seed copies to our own inboxes (recontact-forced: seeds repeat per canary).
    seed_list = [s.strip() for s in seeds.split(",") if s.strip()]
    if seed_list:
        src = run_dir / str(args.get("in", ""))
        import csv as _csv

        with src.open(encoding="utf-8", newline="") as f:
            first = next(_csv.DictReader(f), None)
        if first:
            seed_file = run_dir / "canary.seeds.csv"
            with seed_file.open("w", encoding="utf-8", newline="") as f:
                w = _csv.DictWriter(f, fieldnames=["email", "subject", "body"])
                w.writeheader()
                for s in seed_list:
                    w.writerow({"email": s, "subject": f"[CANARY {run_id}] " + first["subject"],
                                "body": first["body"]})
            run_send(["--allow-recontact"], str(seed_file))

    marker.write_text(datetime.now(UTC).isoformat())
    events.emit("canary.sent", count=count, seeds=seed_list)
    typer.echo(
        f"canary.run: sent {count} live + {len(seed_list)} seeds. "
        "Check the inboxes; resume to approve, or kill the run to stop.",
        err=True,
    )
    raise typer.Exit(config.PAUSE_EXIT_CODE)


# ---- report.write -----------------------------------------------------------------


@app.command("report-write")
def report_write():
    """runs/<id>/report.md + SKILL.md changelog line + skills/INDEX.md refresh."""
    run_dir, skill_dir, run_id, skill = _ctx()
    evts = list(io.read_jsonl(run_dir / "events.jsonl"))
    mirror = list(io.read_jsonl(run_dir / "ledger.jsonl"))

    sent = sum(1 for m in mirror if m.get("status") == "sent")
    failed = sum(1 for m in mirror if m.get("status") == "failed")
    skipped = sum(1 for e in evts if e.get("event") == "claim.skipped")
    suppressed = sum(1 for e in evts if e.get("event") == "claim.suppressed")
    steps_done = [e for e in evts if e.get("event") == "step.completed" and e.get("source") == "runner"]
    started = next((e["ts"] for e in evts if e.get("event") == "run.started"), "")
    counters = [e for e in evts if e.get("event", "").endswith((".summary", ".sourced", ".enriched",
                                                                ".checked", ".rendered", ".filtered"))]
    counter_lines = "\n".join(f"- `{e['event']}`: " + ", ".join(
        f"{k}={v}" for k, v in e.items()
        if k not in ("ts", "run_id", "event", "level", "source")) for e in counters)

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    report = f"""# Run report — {run_id}

- skill: `{skill}` · started: {started} · reported: {now}
- steps completed: {len(steps_done)}
- ledger: **{sent} sent**, {skipped} skipped (already contacted), {suppressed} suppressed, {failed} failed

## Step counters

{counter_lines or "- (none)"}

## Warnings/errors

{chr(10).join("- " + str(e.get("event")) + ": " + str(e.get("reason", e.get("detail", ""))[:120]) for e in evts if e.get("level") in ("warn", "error")) or "- (none)"}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")

    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        text = skill_md.read_text(encoding="utf-8")
        if "## Changelog" not in text:
            text += "\n## Changelog\n"
        text += f"- {now}: run `{run_id}` — {sent} sent, {skipped} skipped, {failed} failed\n"
        skill_md.write_text(text, encoding="utf-8")

    _update_index(skill, run_id)
    events.emit("report.written")
    typer.echo(f"report.write: {run_dir / 'report.md'}")


def _update_index(skill: str, run_id: str) -> None:
    index = config.skills_dir() / "INDEX.md"
    if not index.exists():
        return
    lines = index.read_text(encoding="utf-8").splitlines()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    for i, line in enumerate(lines):
        if line.startswith(f"| {skill} ") or line.startswith(f"|{skill}"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4:
                cells[3] = f"{today} (`{run_id}`)"
                lines[i] = "| " + " | ".join(cells) + " |"
                index.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    # not present yet → append a row
    lines.append(f"| {skill} | (see SKILL.md) | — | {today} (`{run_id}`) |")
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(app())
