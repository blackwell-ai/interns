import asyncio
import csv
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Awaitable, Callable

import httpx

from . import gmail_auth

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]

_SENDER_ENV_KEYS = {
    "armaan": "ARMAAN",
    "samarjit": "SAMARJIT",
    "ethan": "ETHAN",
}

# After a run reports its result ("Result : N sent"), a healthy run.py exits
# within seconds. If it then goes silent past this grace window it is hung on
# exit — a stranded, uncancellable worker thread (the sourcing look-ahead) is
# holding the interpreter open. Kill it so the sender queue advances instead of
# freezing behind one stuck sender.
_DONE_GRACE_S = 60.0
# Ceiling on normal silence *before* the result line: one LLM domain-generation
# call can take up to ~600s (llm._TIMEOUT_S), so a slow-but-healthy sourcing step
# must not be mistaken for a stall.
_ACTIVE_GAP_S = 660.0


def _test_mode() -> bool:
    """When WIZARD_TEST_MODE is truthy, simulate sends instead of running run.py.
    Read at call time (not import) so the flag can be toggled per process."""
    return os.environ.get("WIZARD_TEST_MODE", "").lower() in ("1", "true", "yes", "on")


def _get_supabase_session_token() -> str:
    refresh_token = os.environ.get("SUPABASE_BOT_REFRESH_TOKEN", "")
    if not refresh_token:
        return os.environ.get("SUPABASE_SECRET_KEY", "")
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SECRET_KEY", "")
    r = httpx.post(
        f"{supabase_url}/auth/v1/token?grant_type=refresh_token",
        json={"refresh_token": refresh_token},
        headers={"apikey": service_key},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def run_campaign(
    item: dict,
    send_update: Callable[[str], Awaitable[None]],
    set_progress: Callable[[str], None] | None = None,
    usage: dict | None = None,
    log_line: Callable[[str], None] | None = None,
) -> str:
    if item.get("n_emails", 0) <= 0:
        return f"{item['icp_label']} via {item['from_name']}: skipped (0 emails)"

    sender_key = item["sender_key"]
    env_key = _SENDER_ENV_KEYS[sender_key]
    name = item["from_name"]

    def _emit(line: str) -> None:
        # Forward to the per-campaign log buffer (when one is wired) so the wizard
        # can answer questions from it later. Never raises into the run loop.
        if log_line:
            try:
                log_line(line)
            except Exception:
                pass

    stamp = time.strftime("%H:%M:%S")
    _emit(f"[{stamp}] === {name} starting: {item['n_emails']} emails | "
          f"ICP: {item['icp_desc']} ===")
    if item.get("direct_leads"):
        n = item["n_emails"]
        await send_update(f":crystal_ball: {name} dispatching {n} scroll"
                          f"{'s' if n != 1 else ''} directly to {item['icp_label']}...")
    else:
        await send_update(f":crystal_ball: {name} begins the work, divining up to "
                          f"{item['n_emails']} leads for {item['icp_label']}...")

    tmp_leads_path: str | None = None  # set below if direct_leads writes a temp CSV

    if _test_mode():
        # Safe rehearsal: emit the same progress/result lines run.py would so the
        # wizard's parsing, progress, and final message are all exercised, but
        # spawn no real send and touch no Hunter credits, Gmail, or Supabase.
        sim = (
            "import sys\n"
            "n=int(sys.argv[1])\n"
            "print(f'{n}/{n} contacts (100%)',flush=True)\n"
            "print(f'Drafted : {n} emails',flush=True)\n"
            "print(f'Sending {n} emails',flush=True)\n"
            "print(f'Result: {n} sent',flush=True)\n"
            "print('Hunter: 0.0 credits',flush=True)\n"
            "print('Hunter-usage: before=0 after=0',flush=True)\n"
        )
        cmd = ["python3", "-u", "-c", sim, str(item["n_emails"])]
        env = {**os.environ}
    else:
        try:
            access_token = gmail_auth.get_access_token(item["email"])
        except Exception as e:
            msg = f"{name}: auth failed — {e}"
            await send_update(msg)
            return msg

        try:
            session_token = _get_supabase_session_token()
        except Exception as e:
            log.warning("Supabase session refresh failed: %s", e)
            session_token = os.environ.get("SUPABASE_SECRET_KEY", "")

        env = {
            **os.environ,
            f"GMAIL_TOKEN_{env_key}": access_token,
            "TOOLBOX_SESSION_TOKEN": session_token,
        }

        template_path = str(REPO_ROOT / "skills" / "campaign" / item["template"])

        if item.get("direct_leads"):
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8")
            # personal_line carries the per-lead opening line for personalized
            # direct sends; run.py's mail-merge fills {{personal_line}} from it.
            fields = ["email", "first_name", "last_name", "company", "title",
                      "domain", "personal_line"]
            writer = csv.DictWriter(tmp, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for lead in item["direct_leads"]:
                writer.writerow({k: lead.get(k) or "" for k in fields})
            tmp.close()
            tmp_leads_path = tmp.name
            cmd = [
                "python3", "-u",
                str(REPO_ROOT / "skills" / "campaign" / "run.py"),
                "--leads", tmp_leads_path,
                "--provider", "clay",
                "--from", item["email"],
                "--from-name", item["from_name"],
                "--cc", item["cc"],
                "--template", template_path,
                "--skip-preflight",
            ]
        else:
            cmd = [
                "python3", "-u",
                str(REPO_ROOT / "skills" / "campaign" / "run.py"),
                "--icp", item["icp_desc"],
                "--provider", "hunter",
                "--from", item["email"],
                "--from-name", item["from_name"],
                "--cc", item["cc"],
                "--limit", str(item["n_emails"]),
                "--template", template_path,
                "--skip-preflight",
            ]
            # GEO pilot: fill {{personal_line}} per brand from an AI-visibility check.
            if item.get("geo"):
                cmd.append("--personalize-visibility")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        env=env,
        cwd=str(REPO_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    sent = 0
    credits: str = ""
    done_summary = False  # flips True once run.py prints its final "Result : N sent"
    hung_killed = False   # True if we killed a process that hung after sending

    try:
        while True:
            gap = _DONE_GRACE_S if done_summary else _ACTIVE_GAP_S
            try:
                raw = await asyncio.wait_for(proc.stdout.readline(), timeout=gap)
            except asyncio.TimeoutError:
                # Silent past the window. If the run already reported its result it
                # is hung on exit; if it went silent mid-sourcing it has stalled.
                # Either way, kill it and move on so the queue does not freeze.
                proc.kill()
                await proc.wait()
                hung_killed = True
                if done_summary:
                    log.warning("[%s] hung after reporting result — killed, advancing", name)
                    await send_update(f":warning: {name}: {sent} sent, but the run hung "
                                      f"on exit — moved on to the next sender.")
                else:
                    log.warning("[%s] no output for %.0fs — killed, advancing", name, gap)
                    await send_update(f":warning: {name}: stalled with no output for "
                                      f"{int(gap)}s — moved on to the next sender.")
                break

            if not raw:
                break  # EOF — process closed stdout and exited cleanly

            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            log.info("[%s] %s", name, line)
            _emit(f"[{name}] {line}")

            # Sourcing progress: a live count of leads located so far. Emitted on
            # every step so the Slack scoreboard's "located" counter climbs (the
            # wizard throttles the actual redraw to respect Slack rate limits).
            m = re.search(r"(\d+)/\d+ contacts \((\d+)%\)", line)
            if m:
                found, pct = int(m.group(1)), int(m.group(2))
                if set_progress:
                    set_progress(f"{name}: {pct}% sourced ({found} located)")
                await send_update(f":mag: {name}: {found} located...")
                continue

            # Drafting milestone: every located lead is composed and the send is
            # starting. Flips the run from "locating" to "sending" on the board.
            m = re.search(r"Drafted\s*:\s*(\d+)", line)
            if m:
                drafted = int(m.group(1))
                if set_progress:
                    set_progress(f"{name}: {drafted} drafted, sending now")
                await send_update(f":scroll: {name}: {drafted} scrolls drafted, "
                                  f"sending now...")
                continue

            # Result line → capture sent count
            m = re.search(r"Result\s*:\s*(\d+)\s+sent", line, re.I)
            if m:
                sent = int(m.group(1))
                done_summary = True
                continue

            # Hunter credits → capture for final message
            m = re.search(r"Hunter\s*:\s*([\d.]+)\s+credits", line)
            if m:
                credits = m.group(1)
                continue

            # Absolute account-counter snapshots → span first sender's "before"
            # to last sender's "after" for an authoritative campaign-wide total.
            m = re.search(r"Hunter-usage\s*:\s*before=(\d+)\s+after=(\d+)", line)
            if m and usage is not None:
                before, after = int(m.group(1)), int(m.group(2))
                if usage.get("before") is None:
                    usage["before"] = before
                usage["after"] = after
                continue

            # Errors worth surfacing
            if re.search(r"\berror\b|traceback|exception|FAILED", line, re.I):
                await send_update(f":warning: {name}: {line[:120]}")

        await proc.wait()
    except asyncio.CancelledError:
        proc.kill()
        await proc.wait()
        raise

    if hung_killed:
        pass  # already messaged above; the sends themselves completed
    elif proc.returncode == 0 or done_summary:
        credits_str = f", {credits} Hunter credits" if credits else ""
        await send_update(f":mage: {name}: {sent} sent{credits_str}.")
    else:
        await send_update(f":warning: {name}: the sending faltered "
                          f"(exit {proc.returncode}).")

    if tmp_leads_path:
        try:
            os.unlink(tmp_leads_path)
        except Exception:
            pass

    if done_summary and proc.returncode != 0:
        status = "OK (hung exit, killed)"
    elif proc.returncode == 0:
        status = "OK"
    else:
        status = f"exit {proc.returncode}"
    _emit(f"[{time.strftime('%H:%M:%S')}] === {name} finished: {sent} sent "
          f"[{status}] ===")
    return f"{item['icp_label']} via {name}: {sent} sent [{status}]"


async def run_all(
    plan: list[dict],
    send_update: Callable[[str], Awaitable[None]],
    set_progress: Callable[[str], None] | None = None,
    log_line: Callable[[str], None] | None = None,
) -> str:
    results = []
    usage: dict = {"before": None, "after": None}
    for item in plan:
        result = await run_campaign(item, send_update, set_progress,
                                    usage=usage, log_line=log_line)
        results.append(result)
    # Authoritative campaign-wide credit spend: the account counter delta across
    # the whole run, not the sum of per-sender deltas (which a shared, latently
    # updated counter makes unreliable to attribute per sender).
    if usage["before"] is not None and usage["after"] is not None:
        total = max(0, usage["after"] - usage["before"])
        await send_update(f"In all, the sending drew {total} Hunter credits.")
    return "\n".join(results)
