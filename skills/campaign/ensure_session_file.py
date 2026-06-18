#!/usr/bin/env python3
"""Write ~/.blackwell/session.json from the keychain if it doesn't exist yet.

Run this before any script that needs Supabase auth in a headless context.
If the keychain has a session, writes it to the file silently.
If not, prints a clear error and exits 1.
"""
import json
import sys
from pathlib import Path

SESSION_FILE = Path.home() / ".blackwell" / "session.json"

if SESSION_FILE.exists():
    sys.exit(0)

try:
    import keyring
    from toolbox.core import config

    raw = keyring.get_password(config.KEYRING_SERVICE, "supabase-session")
    if not raw:
        print("Not signed in — run: toolbox auth login", file=sys.stderr)
        sys.exit(1)

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(raw)
    SESSION_FILE.chmod(0o600)
except Exception as e:
    print(f"Could not write session file: {e}", file=sys.stderr)
    print("Run: toolbox auth login", file=sys.stderr)
    sys.exit(1)
