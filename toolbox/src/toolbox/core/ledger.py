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

import asyncio
import time
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
        """Call a ledger RPC, surviving a mid-run token expiry or a transient
        network blip. A long run (sourcing/sending 1000+ contacts) outlives the
        session JWT this client was built with; on the resulting 401 we force a
        fresh token and retry, rather than trusting the local expiry estimate.
        """
        from toolbox.core import auth, events

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                r = await self._client.post(f"/rest/v1/rpc/{fn}", json=payload)
            except httpx.TransportError as e:  # connection reset/timeout under load
                last_exc = e
                await asyncio.sleep(0.5 * (attempt + 1))
                continue

            if r.status_code == 401 and attempt < 2:
                # Capture full context so a recurrence is fixable, not guessed:
                # the server's error body and how much life the local token had.
                try:
                    token_exp_in = round(auth._jwt_expiry(self._token) - time.time())
                except Exception:
                    token_exp_in = None
                events.emit("ledger.unauthorized", level="warn", fn=fn, attempt=attempt,
                            token_exp_in_s=token_exp_in, body=r.text[:500])
                try:
                    fresh = auth.force_refresh(self._token)
                except Exception as e:
                    events.emit("ledger.refresh_failed", level="warn", fn=fn, reason=str(e)[:200])
                    fresh = ""
                if fresh and fresh != self._token:
                    self._token = fresh
                    self._client.headers["Authorization"] = f"Bearer {fresh}"
                    try:
                        new_exp_in = round(auth._jwt_expiry(fresh) - time.time())
                    except Exception:
                        new_exp_in = None
                    events.emit("ledger.token_refreshed", fn=fn, attempt=attempt,
                                new_token_exp_in_s=new_exp_in)
                    continue  # retry with the new token
                # refresh produced nothing usable — surface the 401 below
                events.emit("ledger.refresh_no_change", level="warn", fn=fn, got_token=bool(fresh))

            r.raise_for_status()
            # void functions come back 204/empty from PostgREST
            return r.json() if r.content.strip() else None

        if last_exc:
            raise last_exc
        raise RuntimeError(f"ledger _rpc {fn} exhausted retries")

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
