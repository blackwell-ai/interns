import os

import httpx

_SENDER_REFRESH_KEYS = {
    "armaan.priyadarshan.29@dartmouth.edu": "GMAIL_REFRESH_TOKEN_ARMAAN",
    "samarjit.deshmukh.29@dartmouth.edu": "GMAIL_REFRESH_TOKEN_SAMARJIT",
    "ethanpzhou@berkeley.edu": "GMAIL_REFRESH_TOKEN_ETHAN",
}


def get_access_token(email: str) -> str:
    """Exchange the stored refresh token for a fresh Gmail access token."""
    key = _SENDER_REFRESH_KEYS.get(email)
    if not key:
        raise ValueError(f"No refresh token configured for {email}")
    refresh_token = os.environ[key]
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(
            f"Token refresh failed for {email}: "
            f"{data.get('error')}: {data.get('error_description')}"
        )
    return data["access_token"]
