"""The contact ledger — the one non-removable behavior (spec §7, plan §3.4).

All writes go through SECURITY DEFINER Postgres functions (RPCs), never direct
table writes: the suppression check + claim insert are one atomic server-side
statement, so there is no check-then-act race and RLS never has to expose one
person's contacts to another. The UNIQUE(channel, recipient) constraint is the
invariant; everything here is just the doorway to it.

The local mirror (runs/<id>/ledger.jsonl) answers "did THIS run already send to
X" for crash-safe resume; Supabase answers "did ANYONE, EVER". Send primitives
append to the mirror the moment the provider call returns, BEFORE mark_sent's
network round-trip (plan §7 item 1).
"""

from __future__ import annotations

from pathlib import Path

import httpx

from toolbox.core import config, io


def canonical(recipient: str) -> str:
    return recipient.strip().lower()


class Ledger:
    """Async client over the ledger RPCs. Inject `client` in tests (respx)."""

    def __init__(self, session_token: str, client: httpx.AsyncClient | None = None):
        self._token = session_token
        self._client = client or httpx.AsyncClient(
            base_url=config.supabase_url(),
            headers={
                "apikey": config.supabase_anon_key(),
                "Authorization": f"Bearer {session_token}",
            },
            timeout=30,
        )

    async def _rpc(self, fn: str, payload: dict) -> object:
        r = await self._client.post(f"/rest/v1/rpc/{fn}", json=payload)
        r.raise_for_status()
        # void functions come back 204/empty from PostgREST
        return r.json() if r.content.strip() else None

    async def claim(self, channel: str, recipient: str, *, skill: str = "", run_id: str = "") -> str:
        """-> 'claimed' | 'skipped' (someone already has them) | 'suppressed'."""
        return str(
            await self._rpc(
                "claim_contact",
                {
                    "p_channel": channel,
                    "p_recipient": canonical(recipient),
                    "p_skill": skill,
                    "p_run_id": run_id,
                },
            )
        )

    async def force_claim(self, channel: str, recipient: str, *, skill: str = "", run_id: str = "") -> str:
        """allow_recontact path — logged loudly server-side. Suppression still wins."""
        return str(
            await self._rpc(
                "force_claim_contact",
                {
                    "p_channel": channel,
                    "p_recipient": canonical(recipient),
                    "p_skill": skill,
                    "p_run_id": run_id,
                },
            )
        )

    async def check(self, channel: str, recipient: str) -> str:
        """Read-only (for --dry-run): -> 'new' | 'contacted' | 'suppressed'."""
        return str(
            await self._rpc(
                "check_contact", {"p_channel": channel, "p_recipient": canonical(recipient)}
            )
        )

    async def mark_sent(self, channel: str, recipient: str, message_hash: str = "") -> None:
        await self._rpc(
            "mark_contact",
            {
                "p_channel": channel,
                "p_recipient": canonical(recipient),
                "p_status": "sent",
                "p_message_hash": message_hash,
            },
        )

    async def mark_failed(self, channel: str, recipient: str, reason: str = "") -> None:
        await self._rpc(
            "mark_contact",
            {
                "p_channel": channel,
                "p_recipient": canonical(recipient),
                "p_status": "failed",
                "p_message_hash": reason[:200],
            },
        )

    async def suppress(self, channel: str, recipient: str, reason: str) -> None:
        """Bounces and opt-outs. Permanent; no override exists."""
        await self._rpc(
            "suppress_contact",
            {"p_channel": channel, "p_recipient": canonical(recipient), "p_reason": reason},
        )

    async def heartbeat(self, run_id: str, skill: str, state: str) -> None:
        """Upsert this run's liveness so the cross-machine reaper can tell a
        paused run (keeps claims) from a dead one (releases them)."""
        await self._rpc("run_heartbeat", {"p_run_id": run_id, "p_skill": skill, "p_state": state})

    async def release_stale_claims(self) -> int:
        """Called by the runner on startup. Releases 'claimed' rows whose run is
        dead (no heartbeat >10 min and not paused). Returns rows released."""
        return int(await self._rpc("release_stale_claims", {}))

    async def aclose(self) -> None:
        await self._client.aclose()


# ---- local mirror (per-run resume) ----------------------------------------


def mirror_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / "ledger.jsonl"


def mirror_append(run_dir: str | Path, channel: str, recipient: str, status: str, **extra) -> None:
    io.append_jsonl(
        mirror_path(run_dir),
        {"channel": channel, "recipient": canonical(recipient), "status": status, **extra},
    )


def mirror_sent(run_dir: str | Path) -> set[str]:
    """Recipients this run has already irreversibly acted on (sent or claimed
    with a provider message id) — skipped on resume."""
    done: set[str] = set()
    for rec in io.read_jsonl(mirror_path(run_dir)):
        if rec.get("status") == "sent":
            done.add(rec["recipient"])
    return done
