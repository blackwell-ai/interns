"""M2 done-when, end to end: "kill the run mid-send, rerun, zero duplicates."

Full stack: runner → subprocess gmail primitive → REAL Postgres ledger (local
Supabase) → fake Gmail HTTP server. The "kill" is the provider's hard quota
wall after 2 sends (a clean mid-send interruption); the rerun must deliver the
remaining recipients exactly once and never re-deliver the first two.
"""

import base64
import http.server
import json
import re
import threading
import uuid

import pytest

from toolbox.core import io, runner

from .test_ledger_integration import _make_user, stack  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration

MAKE_OUTBOX = """\
from pathlib import Path
rows = ["email,subject,body"] + [
    f"r{i}-%s@e2e.test,subject {i},body {i}" for i in range(5)
]
Path("outbox.csv").write_text("\\n".join(rows) + "\\n")
"""


class FakeGmail(http.server.BaseHTTPRequestHandler):
    sends: list[str] = []
    crash_after = 2  # then: hard quota wall

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        raw = base64.urlsafe_b64decode(body["raw"] + "=" * (-len(body["raw"]) % 4)).decode()
        to = re.search(r"^To: (.+)$", raw, re.M).group(1).strip()
        cls = type(self)
        if cls.crash_after is not None and len(cls.sends) >= cls.crash_after:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Daily user sending limit exceeded")
            return
        cls.sends.append(to)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"id": f"m-{len(cls.sends)}"}).encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def fake_gmail():
    FakeGmail.sends = []
    FakeGmail.crash_after = 2
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeGmail)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_crash_mid_send_then_resume_zero_duplicates(stack, fake_gmail, tmp_path, monkeypatch):  # noqa: F811
    jwt = _make_user(stack, "e2e")
    # recipients must be globally unique: the ledger PERSISTS across test
    # sessions and would (correctly!) skip anyone contacted by a prior run
    uniq = uuid.uuid4().hex[:10]

    # env inherited by the runner's subprocesses
    monkeypatch.setenv("SUPABASE_URL", stack["url"])
    monkeypatch.setenv("SUPABASE_ANON_KEY", stack["anon"])
    monkeypatch.setenv("TOOLBOX_SESSION_TOKEN", jwt)
    monkeypatch.setenv("TOOLBOX_TOKEN_GMAIL", "fake-token")
    monkeypatch.setenv("TOOLBOX_GMAIL_API_BASE", fake_gmail)

    (tmp_path / ".git").mkdir()
    skill = tmp_path / "skills" / "e2e-send"
    (skill / "steps").mkdir(parents=True)
    (skill / "steps" / "make_outbox.py").write_text(MAKE_OUTBOX % uniq)
    (skill / "flow.yaml").write_text(
        """\
steps:
  - python: {script: steps/make_outbox.py}
  - gmail.send: {in: outbox.csv, from: e2e@test.local, concurrency: 1}
"""
    )
    monkeypatch.chdir(tmp_path)

    # Run 1: the provider wall hits after 2 sends → the step fails cleanly.
    with pytest.raises(runner.FlowError, match="gmail.send"):
        runner.run_skill("e2e-send", root=tmp_path)
    assert len(FakeGmail.sends) == 2

    run_dir = next(d for d in (tmp_path / "runs").iterdir() if d.is_dir())
    status = json.loads((run_dir / "status.json").read_text())
    assert status["state"] == "failed"

    # Run 2: wall lifted; resume must deliver ONLY the remaining three.
    FakeGmail.crash_after = None
    state = runner.resume(run_dir.name, root=tmp_path)
    assert state == "done"

    assert len(FakeGmail.sends) == 5, FakeGmail.sends
    assert len(set(FakeGmail.sends)) == 5, f"duplicate send! {FakeGmail.sends}"

    # The mirror agrees: every recipient recorded sent exactly once.
    mirror = [m for m in io.read_jsonl(run_dir / "ledger.jsonl") if m["status"] == "sent"]
    assert len(mirror) == 5
    assert len({m["recipient"] for m in mirror}) == 5
