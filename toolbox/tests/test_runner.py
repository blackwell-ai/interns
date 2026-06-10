"""Runner tests: toy flows end-to-end offline, kill-and-resume, pause/resume,
clarify re-resolution, and the M3 fork proof (removed steps demonstrably don't run).

The toy skills use the `python:` escape hatch + the throttle primitive so no
network or auth is involved.
"""

import json
from pathlib import Path

import pytest

from toolbox.core import config, runner

APPEND_SCRIPT = """\
import sys
from pathlib import Path
# appends one line per execution — proves how many times the step ran
Path("trace.txt").open("a").write(sys.argv[sys.argv.index("--tag") + 1] + "\\n")
"""

FAIL_ONCE_SCRIPT = """\
import sys
from pathlib import Path
sentinel = Path("already_failed.marker")
if not sentinel.exists():
    sentinel.touch()
    sys.exit(1)   # simulated crash on first attempt
Path("trace.txt").open("a").write("flaky-ok\\n")
"""

PAUSE_ONCE_SCRIPT = """\
import sys
from pathlib import Path
marker = Path("approved.marker")
if not marker.exists():
    marker.touch()
    sys.exit(75)  # pause for the human
Path("trace.txt").open("a").write("gate-passed\\n")
"""


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / "runs").mkdir()
    monkeypatch.chdir(tmp_path)
    # Keep heartbeat RPCs fully offline & instant.
    monkeypatch.setattr(runner, "_rpc_sync", lambda fn, payload: None)
    return tmp_path


def make_skill(repo: Path, name: str, flow: str, inputs: str = "", scripts: dict | None = None):
    d = repo / "skills" / name
    (d / "steps").mkdir(parents=True)
    (d / "flow.yaml").write_text(flow)
    if inputs:
        (d / "inputs.yaml").write_text(inputs)
    for fname, content in (scripts or {}).items():
        (d / "steps" / fname).write_text(content)
    return d


def trace(run_dir: Path) -> list[str]:
    p = run_dir / "trace.txt"
    return p.read_text().splitlines() if p.exists() else []


def events_of(run_dir: Path, kind: str) -> list[dict]:
    out = []
    for line in (run_dir / "events.jsonl").read_text().splitlines():
        e = json.loads(line)
        if e.get("event") == kind and e.get("source") == "runner":
            out.append(e)
    return out


def test_flow_runs_to_done_with_input_substitution(repo):
    make_skill(repo, "toy", """\
steps:
  - python: {script: steps/append.py, tag: "{{label}}-one"}
  - python: {script: steps/append.py, tag: "{{label}}-two"}
""", inputs="label: hello\n", scripts={"append.py": APPEND_SCRIPT})
    run_dir, state = runner.run_skill("toy", root=repo)
    assert state == "done"
    assert trace(run_dir) == ["hello-one", "hello-two"]
    assert len(events_of(run_dir, "step.completed")) == 2


def test_kill_and_resume_skips_completed_steps(repo):
    """The M2 'kill the run mid-send, rerun, zero duplicates' shape, offline:
    step 1 runs once and only once even though the run is executed twice."""
    make_skill(repo, "flaky", """\
steps:
  - python: {script: steps/append.py, tag: first}
  - python: {script: steps/fail_once.py}
  - python: {script: steps/append.py, tag: third}
""", scripts={"append.py": APPEND_SCRIPT, "fail_once.py": FAIL_ONCE_SCRIPT})

    with pytest.raises(runner.FlowError, match="step 1"):
        runner.run_skill("flaky", root=repo)
    run_dir = next((repo / "runs").iterdir())
    assert trace(run_dir) == ["first"]  # crashed at step 1

    state = runner.resume(run_dir.name, root=repo)
    assert state == "done"
    # 'first' appears exactly once → completed steps were not re-executed.
    assert trace(run_dir) == ["first", "flaky-ok", "third"]


def test_pause_and_resume_gate(repo):
    make_skill(repo, "gated", """\
steps:
  - python: {script: steps/gate.py}
  - python: {script: steps/append.py, tag: after-gate}
""", scripts={"append.py": APPEND_SCRIPT, "gate.py": PAUSE_ONCE_SCRIPT})
    run_dir, state = runner.run_skill("gated", root=repo)
    assert state == "paused"
    assert trace(run_dir) == []
    status = json.loads((run_dir / "status.json").read_text())
    assert status["state"] == "paused"

    state = runner.resume(run_dir.name, root=repo)
    assert state == "done"
    assert trace(run_dir) == ["gate-passed", "after-gate"]


def test_fork_removed_step_demonstrably_didnt_run(repo):
    """M3 done-when: fork ships with zero toolbox edits and the removed step's
    events are absent from the fork's run."""
    make_skill(repo, "original", """\
steps:
  - python: {script: steps/append.py, tag: work}
  - python: {script: steps/append.py, tag: canary-stand-in}
  - python: {script: steps/append.py, tag: report}
""", inputs="label: x\n", scripts={"append.py": APPEND_SCRIPT})

    fork_dir = runner.fork("original", "original-yoga", root=repo)
    # the one-minute human edit: delete the middle step
    flow = fork_dir / "flow.yaml"
    flow.write_text("\n".join(line for line in flow.read_text().splitlines()
                              if "canary-stand-in" not in line) + "\n")

    run_dir, state = runner.run_skill("original-yoga", root=repo)
    assert state == "done"
    assert trace(run_dir) == ["work", "report"]  # removed step never executed
    started = [e["step"] for e in events_of(run_dir, "step.started")]
    assert all("canary" not in s for s in started)

    # original is untouched
    run_dir2, _ = runner.run_skill("original", root=repo)
    assert trace(run_dir2) == ["work", "canary-stand-in", "report"]


def test_clarify_reresolves_flow_from_edited_inputs(repo, monkeypatch):
    """Inputs edited at the clarify gate must reach later steps (runner
    re-substitutes the flow after clarify.ask completes)."""
    make_skill(repo, "clar", """\
steps:
  - clarify.ask: {}
  - python: {script: steps/append.py, tag: "{{label}}"}
""", inputs="label: BEFORE\n", scripts={"append.py": APPEND_SCRIPT})

    # Headless + no assume-yes → clarify pauses first.
    run_dir, state = runner.run_skill("clar", root=repo)
    assert state == "paused"
    (run_dir / "inputs.yaml").write_text("label: AFTER\n")  # the human's edit
    state = runner.resume(run_dir.name, root=repo)
    assert state == "done"
    assert trace(run_dir) == ["AFTER"]


def test_undefined_input_is_a_clear_error(repo):
    make_skill(repo, "broken", """\
steps:
  - python: {script: steps/append.py, tag: "{{nope}}"}
""", scripts={"append.py": APPEND_SCRIPT})
    with pytest.raises(runner.FlowError, match="undefined input"):
        runner.run_skill("broken", root=repo)


def test_pause_exit_code_constant():
    assert config.PAUSE_EXIT_CODE == 75
