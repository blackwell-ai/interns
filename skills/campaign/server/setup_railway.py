#!/usr/bin/env python3
"""Set all Railway variables for the campaign bot.

Usage:
  GOOGLE_OAUTH_CLIENT_SECRET=<secret> python3 skills/campaign/server/setup_railway.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = REPO_ROOT / "credentials" / ".env"
GOG_CREDS = Path.home() / "Library" / "Application Support" / "gogcli" / "credentials.json"

ACCOUNTS = {
    "ARMAAN": "armaan.priyadarshan.29@dartmouth.edu",
    "SAMARJIT": "samarjit.deshmukh.29@dartmouth.edu",
    "ETHAN": "ethanpzhou@berkeley.edu",
}


def read_env(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.split("#")[0].strip()
    return out


def get_refresh_token(email: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = f.name
    try:
        r = subprocess.run(
            ["gog", "auth", "tokens", "export", email,
             "--out", tmp, "--overwrite", "--no-input"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip())
        data = json.loads(Path(tmp).read_text())
        rt = data.get("refresh_token", "")
        if not rt:
            raise RuntimeError("no refresh_token in export")
        return rt
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def rset(key: str, value: str) -> None:
    r = subprocess.run(
        ["railway", "variables", "set", f"{key}={value}"],
        capture_output=True, text=True,
    )
    status = "OK " if r.returncode == 0 else "ERR"
    print(f"  {status} {key}")
    if r.returncode != 0:
        print(f"      {r.stderr.strip()[:120]}")


def main() -> None:
    dotenv = read_env(ENV_PATH)
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or dotenv.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    if not client_secret:
        print("ERROR: GOOGLE_OAUTH_CLIENT_SECRET not found in env or credentials/.env")
        sys.exit(1)
    gog = json.loads(GOG_CREDS.read_text())
    client_id = gog.get("client_id", "")

    print("Setting base variables...")
    rset("GOOGLE_OAUTH_CLIENT_ID", client_id)
    rset("GOOGLE_OAUTH_CLIENT_SECRET", client_secret)
    rset("TELEGRAM_BOT_TOKEN", dotenv.get("TELEGRAM_BOT_TOKEN", ""))
    rset("TELEGRAM_CHAT_ID", dotenv.get("TELEGRAM_CHAT_ID", ""))
    rset("ANTHROPIC_API_KEY", dotenv.get("ANTHROPIC_API_KEY", ""))
    rset("TOOLBOX_TOKEN_HUNTER", dotenv.get("TOOLBOX_TOKEN_HUNTER", ""))
    rset("SUPABASE_URL", dotenv.get("SUPABASE_URL", ""))
    rset("SUPABASE_SECRET_KEY", dotenv.get("SUPABASE_SECRET_KEY", ""))
    rset("REMINDER_HOUR", "9")
    rset("REMINDER_MINUTE", "0")
    rset("REMINDER_TZ", "America/New_York")

    print("\nExtracting and setting Gmail refresh tokens...")
    for key, email in ACCOUNTS.items():
        try:
            rt = get_refresh_token(email)
            rset(f"GMAIL_REFRESH_TOKEN_{key}", rt)
        except Exception as e:
            print(f"  ERR GMAIL_REFRESH_TOKEN_{key}: {e}")
            print(f"      Run: gog auth add {email} --services gmail")

    print("\nAll done.")


if __name__ == "__main__":
    main()
