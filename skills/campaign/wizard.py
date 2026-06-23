#!/usr/bin/env python3
"""Interactive wizard for the campaign pipeline.

Prompts for all required parameters, previews the email in the terminal,
sends a test copy to shamit.dsouza@gmail.com, then streams run.py output live.

Usage:
  python3 skills/campaign/wizard.py
  toolbox/.venv/bin/python skills/campaign/wizard.py
"""
from __future__ import annotations

import asyncio
import base64
import email.mime.multipart
import email.mime.text
import html as _html_mod
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).parent
REPO_ROOT  = SKILL_DIR.parent.parent
RUN_PY     = SKILL_DIR / "run.py"
TEMPLATES  = SKILL_DIR / "templates"
PYTHON     = REPO_ROOT / "toolbox" / ".venv" / "bin" / "python"
DOTENV     = REPO_ROOT / "credentials" / ".env"

TEST_EMAIL = "shamit.dsouza@gmail.com"

# ── Sender roster (mirrors send.sh + FOUNDERS.md) ───────────────────────────

SENDERS = [
    ("samarjit", "Samarjit Deshmukh",  "samarjit.deshmukh.29@dartmouth.edu"),
    ("armaan",   "Armaan Priyadarshan", "armaan.priyadarshan.29@dartmouth.edu"),
    ("ethan",    "Ethan Zhou",          "ethanpzhou@berkeley.edu"),
    ("shamit",   "Shamit",              "shamitd@stanford.edu"),
]

# Senders used in "all three" mode (excludes shamit).
STUDENT_SENDERS = [s for s in SENDERS if s[0] != "shamit"]

def _cc_for(key: str) -> str:
    return ",".join(addr for k, _, addr in SENDERS if k != key)

# ── Prompt helpers ───────────────────────────────────────────────────────────

def _ask(prompt: str, default: str = "") -> str:
    display = f"{prompt} [{default}]: " if default else f"{prompt}: "
    try:
        val = input(display).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val if val else default


def _choose(prompt: str, options: list[tuple[str, str]], default: int = 1) -> int:
    print(f"\n{prompt}:")
    for i, (label, desc) in enumerate(options, 1):
        marker = " (default)" if i == default else ""
        suffix = f"  — {desc}" if desc else ""
        print(f"  [{i}] {label}{suffix}{marker}")
    while True:
        raw = _ask("Choose", str(default))
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print(f"  Please enter a number 1-{len(options)}")


def _confirm(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    raw  = _ask(f"{prompt} ({hint})", "y" if default else "n").lower()
    return raw in ("y", "yes")

# ── Env loader ───────────────────────────────────────────────────────────────

def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)

# ── Import bootstrap ─────────────────────────────────────────────────────────

def _bootstrap_imports() -> None:
    """Add toolbox and repo root to sys.path — same setup as run.py."""
    repo = str(REPO_ROOT)
    tb   = str(REPO_ROOT / "toolbox" / "src")
    if repo not in sys.path:
        sys.path.insert(0, repo)
    if tb not in sys.path:
        sys.path.insert(0, tb)

# ── HTML helpers (mirrors run.py) ────────────────────────────────────────────

def _html_to_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return _html_mod.unescape(text).strip()


def _text_to_html(text: str) -> str:
    escaped   = _html_mod.escape(text)
    html_body = escaped.replace("\n\n", "<br><br>").replace("\n", "<br>")
    return (
        '<div style="font-family:Arial,sans-serif;font-size:14px;'
        f'line-height:1.6;color:#333;">{html_body}</div>'
    )

# ── Preview ──────────────────────────────────────────────────────────────────

_PREVIEW_DEFAULTS: dict[str, str] = {
    "first_name":      "Alex",
    "last_name":       "Smith",
    "company":         "Acme Co",
    "title":           "CEO",
    "domain":          "acme.co",
}


def _resolve_preview_template(template_arg: str, config_arg: str) -> tuple[str, str, str]:
    """Return (subject_t, body_t, default_segment_phrase).

    In custom-ICP mode: use template_arg.
    In mix mode: use first segment's template_a + its segment_phrase.
    """
    if template_arg:
        path = Path(template_arg)
        seg_phrase = ""
    else:
        mix_path = Path(config_arg) if config_arg else SKILL_DIR / "icp_mix.toml"
        data  = tomllib.loads(mix_path.read_text())
        segs  = data.get("segments", [])
        if not segs:
            return "", "", ""
        first    = segs[0]
        tpl_rel  = first.get("template_a", "templates/template_b.md")
        path     = SKILL_DIR / tpl_rel
        seg_phrase = first.get("segment_phrase", "")

    _bootstrap_imports()
    from toolbox.primitives.compose import lib as compose_lib  # noqa: PLC0415
    text = path.read_text(encoding="utf-8")
    subject_t, body_t = compose_lib.parse_template(text)
    return subject_t, body_t, seg_phrase


def _compose_example(
    template_arg: str,
    config_arg: str,
    sender_name: str,
    segment_phrase: str,
) -> tuple[str, str, str]:
    """Return (subject, body_text, body_html) with example values filled in."""
    _bootstrap_imports()
    from toolbox.primitives.compose import lib as compose_lib  # noqa: PLC0415

    subject_t, body_t, default_phrase = _resolve_preview_template(template_arg, config_arg)
    if not subject_t:
        return "", "", ""

    values = {
        **_PREVIEW_DEFAULTS,
        "from_name":      sender_name,
        "segment_phrase": segment_phrase or default_phrase or "running your business",
    }

    subject   = compose_lib.render(subject_t, values)
    body_rend = compose_lib.render(body_t, values)
    is_html   = body_rend.lstrip().startswith("<")
    body_text = _html_to_text(body_rend) if is_html else body_rend
    body_html = body_rend if is_html else _text_to_html(body_rend)
    return subject, body_text, body_html


def _show_preview(subject: str, body_text: str) -> None:
    width = 60
    print()
    print("─" * width)
    print("Email preview (example recipient: Alex Smith, Acme Co)")
    print("─" * width)
    print(f"Subject: {subject}")
    print()
    for line in body_text.splitlines():
        print(f"  {line}")
    print("─" * width)

# ── Test email ───────────────────────────────────────────────────────────────

async def _send_test_email(
    from_: str,
    from_name: str,
    subject: str,
    body_text: str,
    body_html: str,
) -> None:
    import httpx  # noqa: PLC0415

    _bootstrap_imports()
    from skills.campaign import gog_auth  # noqa: PLC0415

    token = gog_auth.get_access_token(from_)

    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg["Subject"] = f"[TEST] {subject}"
    msg["From"]    = f"{from_name} <{from_}>" if from_name else from_
    msg["To"]      = TEST_EMAIL
    msg.attach(email.mime.text.MIMEText(body_text, "plain"))
    msg.attach(email.mime.text.MIMEText(body_html, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {token}"},
            json={"raw": raw},
        )
        resp.raise_for_status()

# ── Hunter credit check ───────────────────────────────────────────────────────

def _check_hunter_credits(needed: int) -> None:
    """Warn (and optionally abort) if remaining Hunter credits look insufficient.

    'needed' is an estimate — actual usage depends on how many domains pass
    the free pre-check. Uses ~1.5x as a buffer. Silently skips if the key is
    missing or the API call fails.
    """
    key = os.environ.get("TOOLBOX_TOKEN_HUNTER", "")
    if not key:
        return
    try:
        import httpx  # noqa: PLC0415
        r = httpx.get(
            "https://api.hunter.io/v2/account",
            params={"api_key": key},
            timeout=10,
        )
        if r.status_code != 200:
            return
        remaining = int(
            (r.json().get("data") or {})
            .get("requests", {})
            .get("credits", {})
            .get("remaining") or 0
        )
    except Exception:
        return

    # Credits are per domain searched, not per email. Use 1.5x as a buffer
    # to account for domains that cost a credit but yield nothing.
    estimated = int(needed * 1.5)
    print(f"\n  Hunter credits remaining: {remaining}")
    print(f"  Estimated needed (~1.5x emails as buffer): {estimated}")

    if remaining < estimated:
        print(
            f"\n  Warning: {remaining} credits may not cover {estimated} estimated "
            f"domain searches for {needed} emails."
        )
        if not _confirm("  Proceed anyway?", default=False):
            print("Aborted.")
            sys.exit(0)

# ── Command builder ───────────────────────────────────────────────────────────

def _build_cmd(
    sender_email: str,
    sender_name: str,
    cc: str,
    limit: int,
    provider: str,
    icp_arg: str,
    config_arg: str,
    template_arg: str,
    segment_phrase: str,
    experiment: bool,
    dry_run: bool,
) -> list[str]:
    cmd = [
        str(PYTHON), "-u", str(RUN_PY),
        "--from",      sender_email,
        "--from-name", sender_name,
        "--cc",        cc,
        "--limit",     str(limit),
        "--provider",  provider,
    ]
    if icp_arg:
        cmd += ["--icp", icp_arg]
    if config_arg:
        cmd += ["--config", config_arg]
    if template_arg:
        cmd += ["--template", template_arg]
    if segment_phrase:
        cmd += ["--segment-phrase", segment_phrase]
    if experiment:
        cmd.append("--experiment")
    if dry_run:
        cmd.append("--dry-run")
    return cmd

# ── Runner ────────────────────────────────────────────────────────────────────

def _run_cmd(cmd: list[str]) -> int:
    """Stream a run.py process to stdout. Returns exit code."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
        text=True,
        bufsize=1,
    )
    assert proc.stdout
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
    proc.wait()
    return proc.returncode

# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\nCampaign Wizard")
    print("=" * 48)

    # 0. Send mode: single sender or split across all three
    mode_idx = _choose("Send mode", [
        ("Single sender",      "choose one account to send from"),
        ("All three senders",  "split N evenly across Samarjit, Armaan, Ethan"),
    ], default=1)
    all_senders_mode = (mode_idx == 1)

    # 1. Sender(s)
    if not all_senders_mode:
        sender_opts = [(name, addr) for _, name, addr in SENDERS]
        sender_idx  = _choose("Who is sending", sender_opts, default=1)
        active_senders = [SENDERS[sender_idx]]
    else:
        active_senders = STUDENT_SENDERS

    # preview + test email always come from the first active sender
    _, preview_sender_name, preview_sender_email = active_senders[0]

    # 2. ICP mode
    mode_opts = [
        ("ICP mix file", "distribute N emails across pre-defined segments"),
        ("Custom ICP",   "describe your target in natural language"),
    ]
    icp_mode = _choose("Target mode", mode_opts, default=1)

    icp_arg        = ""
    config_arg     = ""
    template_arg   = ""
    segment_phrase = ""

    if icp_mode == 0:
        mixes    = sorted(SKILL_DIR.glob("icp_mix*.toml"))
        mix_opts = [(p.name, _mix_summary(p)) for p in mixes]
        mix_idx  = _choose("ICP mix file", mix_opts, default=1)
        chosen   = mixes[mix_idx]
        if chosen.name != "icp_mix.toml":
            config_arg = str(chosen)
        print(f"\n  Segments in {chosen.name}:")
        for seg in _mix_segments(chosen):
            print(f"    · {seg}")

    else:
        print()
        icp_arg = _ask("ICP description (e.g. 'DTC home fitness brands')")
        if not icp_arg:
            print("ICP description is required.")
            sys.exit(1)

        tpls     = sorted(TEMPLATES.glob("*.md"))
        tpl_opts = [(p.name, "") for p in tpls]
        tpl_idx  = _choose("Template", tpl_opts, default=1)
        template_arg = str(tpls[tpl_idx])

        if "template_b" in Path(template_arg).name:
            print("  (template_b uses {{segment_phrase}} — e.g. 'running a DTC brand')")
            segment_phrase = _ask("  Segment phrase", "")

    # 3. Number of emails
    print()
    if all_senders_mode:
        limit_raw = _ask(
            f"Total emails to send (split evenly across {len(active_senders)} senders)", "60"
        )
    else:
        limit_raw = _ask("Number of emails to send", "20")
    try:
        limit = int(limit_raw)
    except ValueError:
        print("Must be a number.")
        sys.exit(1)

    if all_senders_mode and limit < len(active_senders):
        print(f"Need at least {len(active_senders)} emails to split across {len(active_senders)} senders.")
        sys.exit(1)

    # 4. Provider
    prov_opts = [
        ("hunter", "find + verify via Hunter API"),
        ("apollo", "find + verify via Apollo"),
    ]
    prov_idx = _choose("Email provider", prov_opts, default=1)
    provider = ["hunter", "apollo"][prov_idx]

    # 5. A/B experiment?
    experiment = _confirm("\nA/B experiment (split 50/50 with a variant email)", default=False)

    # 6. Dry run?
    dry_run = _confirm("Dry run (compose without sending)", default=True)

    # ── Load env + check Hunter credits ──────────────────────────────────────

    _load_dotenv(DOTENV)
    _bootstrap_imports()

    if provider == "hunter":
        _check_hunter_credits(limit)

    # ── Compose example + preview ────────────────────────────────────────────

    try:
        subject, body_text, body_html = _compose_example(
            template_arg, config_arg, preview_sender_name, segment_phrase
        )
        if subject:
            _show_preview(subject, body_text)
        else:
            print("\n(no template to preview)")
    except Exception as e:
        print(f"\n(preview failed: {e})")
        subject, body_text, body_html = "", "", ""

    # ── Per-sender limits ────────────────────────────────────────────────────

    n = len(active_senders)
    per = limit // n
    remainder = limit - per * n
    # first sender absorbs the remainder (e.g. 2101 -> 701, 700, 700)
    per_limits = [per + (remainder if i == 0 else 0) for i in range(n)]

    # ── Summary ──────────────────────────────────────────────────────────────

    print("\n" + "=" * 48)
    print("Summary")
    print("=" * 48)
    if icp_arg:
        print(f"  ICP:         {icp_arg}")
    else:
        print(f"  Mix:         {config_arg or 'icp_mix.toml'}")
    if template_arg:
        print(f"  Template:    {Path(template_arg).name}")
    if segment_phrase:
        print(f"  Seg phrase:  {segment_phrase}")

    if all_senders_mode:
        print(f"  Senders:")
        for (_, sn, se), lim in zip(active_senders, per_limits):
            print(f"    {sn} <{se}>  ({lim} emails)")
    else:
        _, sn, se = active_senders[0]
        cc = _cc_for(active_senders[0][0])
        print(f"  From:        {sn} <{se}>")
        print(f"  CC:          {cc}")

    print(f"  Emails:      {limit}{' total' if all_senders_mode else ''}")
    print(f"  Provider:    {provider}")
    print(f"  A/B:         {'yes' if experiment else 'no'}")
    print(f"  Dry run:     {'YES' if dry_run else 'NO — live send'}")
    print("=" * 48)

    if not _confirm("\nProceed?", default=True):
        print("Aborted.")
        sys.exit(0)

    # ── Test email (from first sender) ───────────────────────────────────────

    if subject and body_html:
        label = f" (from {preview_sender_name})" if all_senders_mode else ""
        print(f"\nSending test email to {TEST_EMAIL}{label}...", flush=True)
        try:
            asyncio.run(_send_test_email(
                preview_sender_email, preview_sender_name, subject, body_text, body_html
            ))
            print(f"Test sent to {TEST_EMAIL}.")
            if not _confirm("Email looks good? Proceed with full campaign", default=True):
                print("Aborted.")
                sys.exit(0)
            print()
        except Exception as e:
            print(f"Test email failed: {e}\n")
    else:
        print(f"\n(skipping test email — could not compose preview)\n")

    # ── Run pipeline(s) ──────────────────────────────────────────────────────

    if not all_senders_mode:
        sender_key, sender_name, sender_email = active_senders[0]
        cc  = _cc_for(sender_key)
        cmd = _build_cmd(
            sender_email, sender_name, cc, limit, provider,
            icp_arg, config_arg, template_arg, segment_phrase,
            experiment, dry_run,
        )
        print("--- Pipeline starting ---\n", flush=True)
        rc = _run_cmd(cmd)
        status = "Done" if rc == 0 else f"Failed (exit {rc})"
        print(f"\n--- {status} ---")
        sys.exit(rc)

    else:
        results: list[tuple[str, int]] = []  # (sender_name, exit_code)
        for i, ((sk, sn, se), lim) in enumerate(zip(active_senders, per_limits)):
            cc  = _cc_for(sk)
            cmd = _build_cmd(
                se, sn, cc, lim, provider,
                icp_arg, config_arg, template_arg, segment_phrase,
                experiment, dry_run,
            )
            print(f"\n{'='*48}")
            print(f"Sender {i+1}/{n}: {sn} ({lim} emails)")
            print(f"{'='*48}\n")

            rc = _run_cmd(cmd)
            results.append((sn, rc))

            if rc != 0:
                print(f"\n  {sn} run exited with code {rc}.")
                if rc == 2:
                    # Preflight failure — likely auth or missing key.
                    # No point continuing; remaining senders will hit the same issue.
                    print("  Preflight failed — stopping. Fix the issue above and retry.")
                    break
                print("  Continuing with next sender...\n")

        # Final summary
        print(f"\n{'='*48}")
        print("All-senders summary")
        print(f"{'='*48}")
        all_ok = True
        for sn, rc in results:
            status = "ok" if rc == 0 else f"failed (exit {rc})"
            print(f"  {sn}: {status}")
            if rc != 0:
                all_ok = False
        skipped = n - len(results)
        if skipped:
            print(f"  ({skipped} sender(s) skipped due to preflight failure)")
        print(f"{'='*48}")
        sys.exit(0 if all_ok else 1)

# ── Mix helpers ───────────────────────────────────────────────────────────────

def _mix_segments(path: Path) -> list[str]:
    try:
        data = tomllib.loads(path.read_text())
        return [s.get("label", "?") for s in data.get("segments", [])]
    except Exception:
        return []


def _mix_summary(path: Path) -> str:
    segs = _mix_segments(path)
    if not segs:
        return ""
    joined = ", ".join(segs[:3])
    suffix = f" +{len(segs)-3} more" if len(segs) > 3 else ""
    return joined + suffix


if __name__ == "__main__":
    main()
