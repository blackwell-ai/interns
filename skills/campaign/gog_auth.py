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
import sys
import tempfile
from pathlib import Path

import httpx

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _gog_creds_path() -> Path:
    """Locate gog's credentials.json across platforms (macOS vs Linux/XDG)."""
    mac = Path.home() / "Library" / "Application Support" / "gogcli" / "credentials.json"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    linux = (Path(xdg) if xdg else Path.home() / ".config") / "gogcli" / "credentials.json"
    for c in (linux, mac):
        if c.exists():
            return c
    return mac if sys.platform == "darwin" else linux


def _client_id() -> str:
    """Read the OAuth client_id from gog's credentials file."""
    creds = _gog_creds_path()
    try:
        data = json.loads(creds.read_text())
        cid = data.get("client_id", "")
        if not cid:
            raise ValueError("client_id missing")
        return cid
    except Exception as e:
        raise RuntimeError(
            f"Could not read gog client_id from {creds}: {e}\n"
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
        data = json.loads(_gog_creds_path().read_text())
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


def get_access_token(account: str) -> str:
    """Return a fresh Gmail access token by exchanging gog's stored refresh token."""
    refresh_token = _refresh_token(account)
    client_id = _client_id()
    client_secret = _client_secret()

    r = httpx.post(
        _GOOGLE_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"Token exchange failed ({r.status_code}): {r.text[:200]}\n"
            f"Run: gog auth add {account} --services gmail"
        )
    token = r.json().get("access_token", "")
    if not token:
        raise RuntimeError("Token exchange succeeded but access_token was empty")
    return token
