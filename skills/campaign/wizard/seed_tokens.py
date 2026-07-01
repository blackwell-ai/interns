#!/usr/bin/env python3
"""Extract Gmail refresh tokens from gog and print fly secrets set commands.

Run this once on the Mac before first deploy:
  python3 skills/campaign/wizard/seed_tokens.py | tee /tmp/fly_secrets.sh
  bash /tmp/fly_secrets.sh

You still need to fill in GOOGLE_OAUTH_CLIENT_SECRET manually.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

ACCOUNTS = {
    "ARMAAN": "armaan.priyadarshan.29@dartmouth.edu",
    "SAMARJIT": "samarjit.deshmukh.29@dartmouth.edu",
    "ETHAN": "ethanpzhou@berkeley.edu",
}

GOG_CREDS = Path.home() / "Library" / "Application Support" / "gogcli" / "credentials.json"


def get_refresh_token(email: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = f.name
    try:
        result = subprocess.run(
            ["gog", "auth", "tokens", "export", email,
             "--out", tmp, "--overwrite", "--no-input"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
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


client_id = json.loads(GOG_CREDS.read_text()).get("client_id", "<client_id>")

print("#!/bin/bash")
print("# Run this script on your Mac to set all Railway variables.")
print("# Requires: npm i -g @railway/cli && railway login && railway link")
print("# Fill in GOOGLE_OAUTH_CLIENT_SECRET before running.\n")

print(f"railway variables set GOOGLE_OAUTH_CLIENT_ID='{client_id}'")
print("railway variables set GOOGLE_OAUTH_CLIENT_SECRET='<paste_from_gcp_console>'")
print(f"railway variables set TELEGRAM_BOT_TOKEN='8851503591:AAFMH5PWVOIffkHQViHC7SgOLZ7E4D4SrNc'")
print(f"railway variables set TELEGRAM_CHAT_ID='8609913087'")
print(f"railway variables set ANTHROPIC_API_KEY='{os.environ.get('ANTHROPIC_API_KEY', '<paste_key>')}'")
print(f"railway variables set REMINDER_HOUR='9'")
print(f"railway variables set REMINDER_MINUTE='0'")
print(f"railway variables set REMINDER_TZ='America/New_York'")

env_path = Path(__file__).resolve().parents[3] / "credentials" / ".env"
hunter_key = ""
supabase_url = ""
supabase_secret = ""
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("TOOLBOX_TOKEN_HUNTER="):
            hunter_key = line.split("=", 1)[1].strip()
        elif line.startswith("SUPABASE_URL="):
            supabase_url = line.split("=", 1)[1].strip()
        elif line.startswith("SUPABASE_SECRET_KEY="):
            supabase_secret = line.split("=", 1)[1].strip()

print(f"railway variables set TOOLBOX_TOKEN_HUNTER='{hunter_key or '<paste_key>'}'")
print(f"railway variables set SUPABASE_URL='{supabase_url or '<paste_url>'}'")
print(f"railway variables set SUPABASE_SECRET_KEY='{supabase_secret or '<paste_key>'}'")
print()

for key, email in ACCOUNTS.items():
    try:
        rt = get_refresh_token(email)
        print(f"railway variables set GMAIL_REFRESH_TOKEN_{key}='{rt}'")
    except Exception as e:
        print(f"# ERROR getting token for {email}: {e}")
        print(f"# Run: gog auth add {email} --services gmail")
        print(f"railway variables set GMAIL_REFRESH_TOKEN_{key}='<paste_token>'")
