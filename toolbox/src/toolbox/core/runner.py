"""The flow runner (spec §6, build plan M1).

Executes a skill's flow.yaml — a declarative step list — top to bottom:

  * resolves {{inputs}} from inputs.yaml (+ CLI overrides) into
    flow.resolved.yaml — the audit record of exactly what ran;
  * shells out to each primitive's CLI (`python -m toolbox.primitives.X.cli`)
    with cwd = the run folder, so step files are plain relative paths;
  * pauses when a step exits PAUSE_EXIT_CODE (clarify.ask, canary.run) and
    resumes from artifacts + events after any interruption;
  * heartbeats runs/<id>/status.json and the Supabase `runs` table so the
    cross-machine reaper can tell paused from dead (plan §3.4).

Resume correctness: a step is "done" iff the runner logged `step.completed`
for its index — artifact existence is not trusted (atomic writes make
artifacts safe, but only the event proves the step finished).
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from ruamel.yaml import YAML

from toolbox.core import config, events, io

yaml = YAML()
yaml.preserve_quotes = True

VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")

# Process steps live in toolbox/process; everything else maps by prefix to
# toolbox/primitives/<prefix>/cli.py. No central registry to maintain.
PROCESS_STEPS = {
    "plan.write": "plan-write",
    "clarify.ask": "clarify-ask",
    "test.smoke": "test-smoke",
    "test.dryrun": "test-dryrun",
    "canary.run": "canary-run",
    "report.write": "report-write",
}


class FlowError(Exception):
    pass


def _step_module(name: str) -> tuple[str, str]:
    if name in PROCESS_STEPS:
        return "toolbox.process.cli", PROCESS_STEPS[name]
    prim, _, cmd = name.partition(".")
    if not cmd:
        raise FlowError(f"step name must be '<primitive>.<command>', got {name!r}")
    return f"toolbox.primitives.{prim}.cli", cmd


def _substitute(value, variables: dict):
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            key = m.group(1)
            if key not in variables:
                raise FlowError(f"flow references undefined input {{{{{key}}}}}")
            return str(variables[key])

        # Fixpoint: an input's value may itself contain {{builtins}}
        # (e.g. sources_csv: "{{skill_dir}}/sources.csv").
        for _ in range(5):
            new = VAR_RE.sub(repl, value)
            if new == value:
                break
            value = new
        return value
    if isinstance(value, dict):
        return {k: _substitute(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, variables) for v in value]
    return value


def _parse_step(step) -> tuple[str, dict]:
    """A step is a single-key mapping: {'apollo.enrich': {...args}} or a bare
    string 'report.write'. The 'python:' key is the escape hatch."""
    if isinstance(step, str):
        return step, {}
    if isinstance(step, dict) and len(step) == 1:
        name, args = next(iter(step.items()))
        return name, dict(args or {})
    raise FlowError(f"malformed step (need one key): {step!r}")


def _args_to_argv(args: dict) -> list[str]:
    argv: list[str] = []
    for k, v in args.items():
        flag = "--" + k.replace("_", "-")
        if isinstance(v, bool):
            if v:
                argv.append(flag)
        elif isinstance(v, list):
            argv += [flag, ",".join(str(x) for x in v)]
        else:
            argv += [flag, str(v)]
    return argv


# ---- run lifecycle ----------------------------------------------------------


def new_run(skill: str, overrides: dict | None = None, root: Path | None = None) -> Path:
    skill_dir = config.skills_dir(root) / skill
    flow_path = skill_dir / "flow.yaml"
    if not flow_path.exists():
        raise FlowError(f"no such skill: {skill} ({flow_path} missing)")

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{skill}-{stamp}-{secrets.token_hex(3)}"
    run_dir = config.runs_dir(root) / run_id
    run_dir.mkdir(parents=True)

    inputs: dict = {}
    inputs_path = skill_dir / "inputs.yaml"
    if inputs_path.exists():
        with inputs_path.open() as f:
            inputs = dict(yaml.load(f) or {})
    inputs.update(overrides or {})

    variables = {
        **inputs,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "skill_dir": str(skill_dir),
        "repo_root": str(config.repo_root(root)),
    }
    with flow_path.open() as f:
        flow = yaml.load(f)
    resolved = _substitute(flow, variables)

    with (run_dir / "flow.resolved.yaml").open("w") as f:
        yaml.dump(resolved, f)
    with (run_dir / "inputs.yaml").open("w") as f:
        yaml.dump(inputs, f)
    io.write_json(run_dir / "status.json", {
        "run_id": run_id, "skill": skill, "state": "running",
        "step_index": 0, "heartbeat": datetime.now(UTC).isoformat(),
    })
    return run_dir


def _reresolve(run_dir: Path, skill_dir: Path, run_id: str) -> None:
    with (run_dir / "inputs.yaml").open() as f:
        inputs = dict(yaml.load(f) or {})
    variables = {
        **inputs,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "skill_dir": str(skill_dir),
        "repo_root": str(config.repo_root(run_dir)),
    }
    with (skill_dir / "flow.yaml").open() as f:
        flow = yaml.load(f)
    with (run_dir / "flow.resolved.yaml").open("w") as f:
        yaml.dump(_substitute(flow, variables), f)


def completed_steps(run_dir: Path) -> set[int]:
    return {
        e["step_index"]
        for e in events.read_all(run_dir)
        if e.get("event") == "step.completed" and e.get("source") == "runner"
    }


# ---- supabase liveness (best-effort: offline runs still work) ---------------


def _rpc_sync(fn: str, payload: dict) -> object | None:
    try:
        from toolbox.core import auth

        token = auth.session_token()
        r = httpx.post(
            f"{config.supabase_url()}/rest/v1/rpc/{fn}",
            json=payload,
            headers={"apikey": config.supabase_anon_key(), "Authorization": f"Bearer {token}"},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


class _Heartbeat:
    """status.json + DB heartbeat every 30s while a step is executing."""

    def __init__(self, run_dir: Path, run_id: str, skill: str):
        self.run_dir, self.run_id, self.skill = run_dir, run_id, skill
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def beat(self, state: str, step_index: int) -> None:
        status = io.read_json(self.run_dir / "status.json")
        status.update(state=state, step_index=step_index,
                      heartbeat=datetime.now(UTC).isoformat())
        io.write_json(self.run_dir / "status.json", status)
        _rpc_sync("run_heartbeat", {"p_run_id": self.run_id, "p_skill": self.skill, "p_state": state})

    def start(self, step_index: int) -> None:
        self._stop.clear()

        def loop():
            while not self._stop.wait(30):
                self.beat("running", step_index)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()


# ---- execution ---------------------------------------------------------------


def execute(run_dir: Path, *, assume_yes: bool = False) -> str:
    """Run all incomplete steps. Returns 'done' | 'paused'. Raises on failure."""
    status = io.read_json(run_dir / "status.json")
    run_id, skill = status["run_id"], status["skill"]
    skill_dir = config.skills_dir(run_dir) / skill

    with (run_dir / "flow.resolved.yaml").open() as f:
        flow = yaml.load(f)
    steps = list(flow.get("steps") or [])
    done = completed_steps(run_dir)

    # Reap claims from dead runs before we start (never touches paused runs).
    _rpc_sync("release_stale_claims", {})

    hb = _Heartbeat(run_dir, run_id, skill)
    env_extra = {
        "TOOLBOX_RUN_DIR": str(run_dir),
        "TOOLBOX_RUN_ID": run_id,
        "TOOLBOX_SKILL": skill,
        "TOOLBOX_SKILL_DIR": str(skill_dir),
    }
    if assume_yes:
        env_extra["TOOLBOX_ASSUME_YES"] = "1"

    index = -1
    while index + 1 < len(steps):
        index += 1
        raw_step = steps[index]
        if index in done:
            continue
        name, args = _parse_step(raw_step)

        if name == "python":  # escape hatch: {python: steps/foo.py, ...args}
            script = args.pop("python", None) or args.pop("script", None)
            if script is None:
                script, args = raw_step["python"], {}
            argv = [sys.executable, str((skill_dir / str(script)).resolve()), *_args_to_argv(args)]
            display = f"python:{script}"
        else:
            module, command = _step_module(name)
            argv = [sys.executable, "-m", module, command, *_args_to_argv(args)]
            display = name

        _emit_runner(run_dir, run_id, "step.started", index, display)
        hb.beat("running", index)
        hb.start(index)
        try:
            proc = subprocess.run(argv, cwd=run_dir, env={**os.environ, **env_extra})
        finally:
            hb.stop()

        if proc.returncode == 0:
            _emit_runner(run_dir, run_id, "step.completed", index, display)
            if name == "clarify.ask":
                # The human may have edited inputs — re-resolve the rest of the
                # flow from the skill's flow.yaml against the updated inputs.
                _reresolve(run_dir, skill_dir, run_id)
                with (run_dir / "flow.resolved.yaml").open() as f2:
                    steps = list((yaml.load(f2) or {}).get("steps") or [])
            continue
        if proc.returncode == config.PAUSE_EXIT_CODE:
            hb.beat("paused", index)
            _emit_runner(run_dir, run_id, "step.paused", index, display)
            print(f"\n⏸  Run paused at step {index} ({display}).")
            print(f"   Act on it, then resume with:  toolbox resume {run_id}")
            return "paused"
        hb.beat("failed", index)
        _emit_runner(run_dir, run_id, "step.failed", index, display, level="error",
                     exit_code=proc.returncode)
        raise FlowError(f"step {index} ({display}) failed with exit code {proc.returncode}")

    hb.beat("done", len(steps))
    _emit_runner(run_dir, run_id, "run.finished", len(steps), "")
    return "done"


def _emit_runner(run_dir: Path, run_id: str, event: str, index: int, step: str,
                 level: str = "info", **extra) -> None:
    io.append_jsonl(run_dir / "events.jsonl", {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "run_id": run_id, "event": event, "level": level,
        "source": "runner", "step_index": index, "step": step, **extra,
    })


def run_skill(skill: str, overrides: dict | None = None, *, assume_yes: bool = False,
              root: Path | None = None) -> tuple[Path, str]:
    run_dir = new_run(skill, overrides, root)
    _emit_runner(run_dir, run_dir.name, "run.started", 0, skill)
    return run_dir, execute(run_dir, assume_yes=assume_yes)


def resume(run_id: str, *, assume_yes: bool = False, root: Path | None = None) -> str:
    run_dir = config.runs_dir(root) / run_id
    if not run_dir.exists():
        raise FlowError(f"no such run: {run_id}")
    return execute(run_dir, assume_yes=assume_yes)


def fork(src_skill: str, dst_skill: str, *, root: Path | None = None) -> Path:
    """The fork reflex (spec §6): copy the folder, note provenance. The human
    (or agent) then edits inputs.yaml / deletes flow lines and runs."""
    skills = config.skills_dir(root)
    src, dst = skills / src_skill, skills / dst_skill
    if not src.exists():
        raise FlowError(f"no such skill: {src_skill}")
    if dst.exists():
        raise FlowError(f"skill already exists: {dst_skill}")
    shutil.copytree(src, dst)
    note = f"\n> Forked from `{src_skill}` on {time.strftime('%Y-%m-%d')}; edit this line with what differs.\n"
    skill_md = dst / "SKILL.md"
    if skill_md.exists():
        skill_md.write_text(skill_md.read_text(encoding="utf-8") + note, encoding="utf-8")
    return dst
