"""Get a Gmail access token from gog's keyring.

Teammates only need `gog auth add <email> --services gmail` once.
This module reads the refresh token gog stored, reads the client
credentials gog stored, and exchanges them directly with Google —
no Gmail keys in .env needed.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import httpx

_GOG_CREDS_PATH = (
    Path.home() / "Library" / "Application Support" / "gogcli" / "credentials.json"
)
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Server mode: executor injects fresh access tokens as env vars keyed by sender.
_SENDER_ENV_KEYS: dict[str, str] = {
    "armaan.priyadarshan.29@dartmouth.edu": "ARMAAN",
    "samarjit.deshmukh.29@dartmouth.edu": "SAMARJIT",
    "ethanpzhou@berkeley.edu": "ETHAN",
    "shamit.dsouza@gmail.com": "SHAMIT",
}


def _client_id() -> str:
    """Read the OAuth client_id from gog's credentials file."""
    try:
        data = json.loads(_GOG_CREDS_PATH.read_text())
        cid = data.get("client_id", "")
        if not cid:
            raise ValueError("client_id missing")
        return cid
    except Exception as e:
        raise RuntimeError(
            f"Could not read gog client_id from {_GOG_CREDS_PATH}: {e}\n"
            "Run: gog auth credentials ~/client_secret.json"
        ) from e


def _client_secret() -> str:
    """Read the OAuth client_secret, preferring gog's credentials file.

    gog writes both client_id and client_secret into credentials.json, so the
    secret there is guaranteed to match the id we read in `_client_id`. The
    keychain can hold a stale secret from an earlier client (Google then rejects
    the pair with `invalid_client`), so it is only a fallback when the file omits
    the secret.
    """
    try:
        data = json.loads(_GOG_CREDS_PATH.read_text())
        if secret := data.get("client_secret", ""):
            return secret
    except Exception:
        pass

    result = subprocess.run(
        ["security", "find-generic-password", "-s", "gogcli", "-w"],
        capture_output=True, text=True, timeout=10,
    )
    secret = result.stdout.strip()
    if result.returncode != 0 or not secret:
        raise RuntimeError(
            "Could not read gog client_secret from credentials.json or keychain.\n"
            "Run: gog auth credentials ~/client_secret.json"
        )
    return secret


def _refresh_token(account: str) -> str:
    """Export and return the refresh token gog has stored for this account."""
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
                f"Run: gog auth add {account} --services gmail"
            )
        data = json.loads(Path(tmp).read_text())
        rt = data.get("refresh_token", "")
        if not rt:
            raise RuntimeError(
                f"No refresh token found for {account}.\n"
                f"Run: gog auth add {account} --services gmail"
            )
        return rt
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _export_access_token(account: str) -> str:
    """Export and return the access token gog has stored for this account, or ''."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = f.name
    try:
        result = subprocess.run(
            ["gog", "auth", "tokens", "export", account,
             "--out", tmp, "--overwrite", "--no-input"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return ""
        data = json.loads(Path(tmp).read_text())
        return data.get("access_token", "")
    except Exception:
        return ""
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _is_token_fresh(account: str) -> bool:
    """Return True if gog's cached access token has more than 5 minutes remaining."""
    from datetime import UTC, datetime

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = f.name
    try:
        result = subprocess.run(
            ["gog", "auth", "tokens", "export", account,
             "--out", tmp, "--overwrite", "--no-input"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return False
        data = json.loads(Path(tmp).read_text())
        access_token = data.get("access_token", "")
        expires_at_str = data.get("access_token_expires_at", "")
        if not access_token or not expires_at_str:
            return False
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        return (expires_at - datetime.now(UTC)).total_seconds() > 300
    except Exception:
        return False
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def get_access_token(account: str) -> str:
    """Return a fresh Gmail access token.

    Server fast path: if GMAIL_TOKEN_{SENDER} is set in env (injected by the
    campaign bot executor), return it directly without touching gog.
    Local fast path: if gog's cached token has >5 min remaining, return it.
    Otherwise, let gog refresh it by making a lightweight Gmail API call.
    """
    env_key = _SENDER_ENV_KEYS.get(account, "")
    if env_key:
        if token := os.environ.get(f"GMAIL_TOKEN_{env_key}"):
            return token

    if _is_token_fresh(account):
        token = _export_access_token(account)
        if token:
            return token

    # Token is expired or missing — force gog to refresh it internally.
    result = subprocess.run(
        ["gog", "gmail", "list", "in:inbox", "--account", account,
         "--limit", "1", "--no-input"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gog failed to refresh token for {account}: {result.stderr[:200]}\n"
            f"Run: gog auth add {account} --services gmail"
        )

    token = _export_access_token(account)
    if not token:
        raise RuntimeError(
            f"Token refresh succeeded but access_token missing for {account}.\n"
            f"Run: gog auth add {account} --services gmail"
        )
    return token
