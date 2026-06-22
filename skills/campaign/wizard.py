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

# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\nCampaign Wizard")
    print("=" * 48)

    # 1. Sender
    sender_opts = [(name, email) for _, name, email in SENDERS]
    sender_idx  = _choose("Who is sending", sender_opts, default=1)
    sender_key, sender_name, sender_email = SENDERS[sender_idx]
    cc = _cc_for(sender_key)

    # 2. ICP mode
    mode_opts = [
        ("ICP mix file", "distribute N emails across pre-defined segments"),
        ("Custom ICP",   "describe your target in natural language"),
    ]
    mode = _choose("Target mode", mode_opts, default=1)

    icp_arg        = ""
    config_arg     = ""
    template_arg   = ""
    segment_phrase = ""

    if mode == 0:
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
    limit_raw = _ask("Number of emails to send", "20")
    try:
        limit = int(limit_raw)
    except ValueError:
        print("Must be a number.")
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

    # ── Compose example + preview ────────────────────────────────────────────

    _load_dotenv(DOTENV)
    _bootstrap_imports()

    try:
        subject, body_text, body_html = _compose_example(
            template_arg, config_arg, sender_name, segment_phrase
        )
        if subject:
            _show_preview(subject, body_text)
        else:
            print("\n(no template to preview)")
    except Exception as e:
        print(f"\n(preview failed: {e})")
        subject, body_text, body_html = "", "", ""

    # ── Build run.py command ─────────────────────────────────────────────────

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
    print(f"  From:        {sender_name} <{sender_email}>")
    print(f"  CC:          {cc}")
    print(f"  Emails:      {limit}")
    print(f"  Provider:    {provider}")
    print(f"  A/B:         {'yes' if experiment else 'no'}")
    print(f"  Dry run:     {'YES' if dry_run else 'NO — live send'}")
    print("=" * 48)

    if not _confirm("\nProceed?", default=True):
        print("Aborted.")
        sys.exit(0)

    # ── Test email ───────────────────────────────────────────────────────────

    if subject and body_html:
        print(f"\nSending test email to {TEST_EMAIL}...", flush=True)
        try:
            asyncio.run(_send_test_email(sender_email, sender_name, subject, body_text, body_html))
            print(f"Test sent to {TEST_EMAIL}.")
            if not _confirm("Email looks good? Proceed with full campaign", default=True):
                print("Aborted.")
                sys.exit(0)
            print()
        except Exception as e:
            print(f"Test email failed: {e}\n")
    else:
        print(f"\n(skipping test email — could not compose preview)\n")

    # ── Run pipeline ─────────────────────────────────────────────────────────

    print("--- Pipeline starting ---\n", flush=True)

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

    rc     = proc.returncode
    status = "Done" if rc == 0 else f"Failed (exit {rc})"
    print(f"\n--- {status} ---")
    sys.exit(rc)

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
