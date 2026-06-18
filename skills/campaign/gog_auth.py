"""Get a Gmail access token from gog's keyring.

Teammates only need `gog auth login <email>` once. This module does the rest:
exports the token, reads it, and cleans up — no credentials in .env needed.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile


def get_access_token(account: str) -> str:
    """Return a fresh Gmail access token from gog's keyring."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = f.name
    try:
        result = subprocess.run(
            ["gog", "auth", "tokens", "export", account,
             "--out", tmp, "--overwrite", "--no-input"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"gog auth tokens export failed: {result.stderr[:200]}\n"
                f"Run: gog auth login {account}"
            )
        data = json.loads(open(tmp).read())
        token = data.get("access_token", "")
        if not token:
            raise RuntimeError("gog export succeeded but access_token was empty")
        return token
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
