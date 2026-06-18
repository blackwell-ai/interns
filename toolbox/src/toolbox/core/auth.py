"""Per-person auth on Supabase (spec §8, plan M0.5).

Two separate OAuth consents (plan §7 item 4 — sign-in is NOT send-authorization):
  1. `toolbox auth login`   — Supabase Google sign-in → identity session.
     Session (refresh token) is stored in the OS keychain, never the repo.
  2. `toolbox auth connect gmail` — a SECOND consent requesting gmail.send +
     gmail.readonly, driven by the `oauth-connect` edge function, which stores
     the refresh token server-side. Provider client-secrets never reach laptops.

`get_token(provider)` exchanges the person's session for a fresh provider
token via the `token-refresh` edge function. API-key providers (clay, anthropic) return the stored key the same way, so no key ever
sits in the repo or an env file.

Headless/test override: TOOLBOX_TOKEN_<PROVIDER> env var short-circuits
get_token, and TOOLBOX_SESSION_TOKEN short-circuits the keychain. These exist
for offline tests and CI — not for production use.
"""

from __future__ import annotations

import base64
import http.server
import json
import os
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

import httpx

from toolbox.core import config

_KEYRING_USER = "supabase-session"


class AuthError(Exception):
    pass


# ---- keychain session storage ----------------------------------------------

_SESSION_FILE = Path.home() / ".blackwell" / "session.json"


def _save_session(session: dict) -> None:
    import keyring

    keyring.set_password(config.KEYRING_SERVICE, _KEYRING_USER, json.dumps(session))
    _SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SESSION_FILE.write_text(json.dumps(session))
    _SESSION_FILE.chmod(0o600)


def _load_session() -> dict | None:
    if tok := os.environ.get("TOOLBOX_SESSION_TOKEN"):
        return {"access_token": tok, "refresh_token": ""}
    import keyring

    raw = keyring.get_password(config.KEYRING_SERVICE, _KEYRING_USER)
    if raw:
        return json.loads(raw)
    # Fallback for headless/cron contexts that can't read the macOS keychain.
    if _SESSION_FILE.exists():
        try:
            return json.loads(_SESSION_FILE.read_text())
        except Exception:
            pass
    return None


def _jwt_expiry(token: str) -> float:
    """Read `exp` from the JWT payload (no signature check — server verifies)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return float(json.loads(base64.urlsafe_b64decode(payload)).get("exp", 0))
    except Exception:
        return 0.0


# ---- login (Supabase GoTrue, Google provider) -------------------------------

_CALLBACK_PAGE = b"""<!doctype html><html><body><script>
// GoTrue returns tokens in the URL *fragment* (never sent to a server), so
// this page forwards the fragment to the local CLI listener via POST.
fetch('/token', {method: 'POST', body: location.hash.slice(1)})
  .then(() => document.body.innerText = 'Signed in - you can close this tab.');
</script>Completing sign-in&hellip;</body></html>"""


def login(timeout_s: int = 180) -> dict:
    """Open the browser for Google sign-in; store the session in the keychain."""
    result: dict = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(_CALLBACK_PAGE)

        def do_POST(self):  # noqa: N802
            body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
            result.update(urllib.parse.parse_qsl(body))
            self.send_response(204)
            self.end_headers()
            done.set()

        def log_message(self, *a):  # silence
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = (
            f"{config.supabase_url()}/auth/v1/authorize?provider=google"
            f"&redirect_to={urllib.parse.quote(f'http://127.0.0.1:{port}/')}"
        )
        print(f"Opening browser for Google sign-in… (or visit: {url})")
        webbrowser.open(url)
        if not done.wait(timeout_s):
            raise AuthError("sign-in timed out")
    finally:
        server.shutdown()

    if "access_token" not in result:
        raise AuthError(f"sign-in failed: {result.get('error_description', result)}")
    session = {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token", ""),
    }
    _save_session(session)
    return session


def session_token() -> str:
    """A valid session JWT, refreshed via GoTrue when within 60s of expiry."""
    if tok := os.environ.get("TOOLBOX_SESSION_TOKEN"):  # tests/CI only
        return tok
    session = _load_session()
    if not session:
        raise AuthError("not signed in — run `toolbox auth login`")
    if _jwt_expiry(session["access_token"]) - time.time() > 60:
        return session["access_token"]
    if not session.get("refresh_token"):
        raise AuthError("session expired — run `toolbox auth login`")
    r = httpx.post(
        f"{config.supabase_url()}/auth/v1/token?grant_type=refresh_token",
        json={"refresh_token": session["refresh_token"]},
        headers={"apikey": config.supabase_anon_key()},
        timeout=30,
    )
    if r.status_code != 200:
        raise AuthError(f"session refresh failed ({r.status_code}) — run `toolbox auth login`")
    data = r.json()
    session = {"access_token": data["access_token"], "refresh_token": data["refresh_token"]}
    _save_session(session)
    return session["access_token"]


def whoami() -> dict:
    r = httpx.get(
        f"{config.supabase_url()}/auth/v1/user",
        headers={"apikey": config.supabase_anon_key(), "Authorization": f"Bearer {session_token()}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ---- provider tokens ---------------------------------------------------------


def get_token(provider: str) -> str:
    """Fresh provider token/key via the token-refresh edge function.

    Never logged, never put in argv (argv is visible in `ps`), never echoed.

    .env shortcut for gmail: set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and
    GMAIL_REFRESH_TOKEN to bypass Supabase entirely (run get_gmail_token.py once).
    """
    if override := os.environ.get(f"TOOLBOX_TOKEN_{provider.upper()}"):
        return override
    if provider == "gmail":
        refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()
        client_id = os.environ.get("GMAIL_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
        if refresh_token and client_id and client_secret:
            return _refresh_gmail_token(refresh_token, client_id, client_secret)
    r = httpx.post(
        f"{config.supabase_url()}/functions/v1/token-refresh",
        json={"provider": provider},
        headers={"apikey": config.supabase_anon_key(), "Authorization": f"Bearer {session_token()}"},
        timeout=30,
    )
    if r.status_code == 404:
        raise AuthError(f"no '{provider}' connection — run `toolbox auth connect {provider}`")
    r.raise_for_status()
    return r.json()["token"]


def _refresh_gmail_token(refresh_token: str, client_id: str, client_secret: str) -> str:
    r = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    tok = r.json()
    if not tok.get("access_token"):
        raise AuthError("Gmail token refresh failed — check GMAIL_REFRESH_TOKEN in credentials/.env")
    return tok["access_token"]


def connect_api_key(provider: str, key: str, account: str = "", org_shared: bool = False) -> None:
    """Store an API-key connection (clay, anthropic). The secret
    goes through the edge function into `connection_secrets` (service-role
    only); only metadata is visible to clients."""
    r = httpx.post(
        f"{config.supabase_url()}/functions/v1/oauth-connect",
        json={
            "action": "store-key",
            "provider": provider,
            "secret": key,
            "account": account,
            "org_shared": org_shared,
        },
        headers={"apikey": config.supabase_anon_key(), "Authorization": f"Bearer {session_token()}"},
        timeout=30,
    )
    r.raise_for_status()


def connect_oauth_start(provider: str) -> str:
    """Begin the second OAuth consent (e.g. Gmail scopes). Returns the URL the
    person opens in a browser; the edge function handles the callback and
    stores the refresh token server-side."""
    r = httpx.post(
        f"{config.supabase_url()}/functions/v1/oauth-connect",
        json={"action": "start", "provider": provider},
        headers={"apikey": config.supabase_anon_key(), "Authorization": f"Bearer {session_token()}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["auth_url"]
