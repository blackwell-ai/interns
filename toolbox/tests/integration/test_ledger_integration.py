"""M0 integration tests against the LOCAL Supabase stack (`supabase start`).

These are the tests the whole project lives on (build plan §5):
  1. claim race      — 20 concurrent claims on one recipient, exactly one winner
  2. two-person      — overlapping recipient sets, union claimed exactly once
  3. RLS             — person A cannot read person B's connections/contacted rows
  4. suppression     — suppressed recipients can never be claimed (even forced)
  5. reaper          — dead runs release claims; paused runs keep them

Run with:  uv run pytest -m integration
Skipped automatically when the local stack isn't up.
"""

import asyncio
import subprocess
import uuid

import httpx
import pytest

from toolbox.core.ledger import Ledger

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def stack():
    """Read URL + keys from `supabase status`; skip if the stack isn't running."""
    try:
        proc = subprocess.run(
            ["supabase", "status", "-o", "env"],
            capture_output=True, text=True, timeout=20,
            cwd=str(__import__("toolbox.core.config", fromlist=["repo_root"]).repo_root()),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("supabase CLI not available")
    if proc.returncode != 0:
        pytest.skip(f"local supabase stack not running: {proc.stderr.strip()[:200]}")
    env = dict(
        line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line
    )
    url = env.get("API_URL", "http://127.0.0.1:54321").strip('"')
    anon = env.get("ANON_KEY", "").strip('"')
    service = env.get("SERVICE_ROLE_KEY", "").strip('"')
    if not anon or not service:
        pytest.skip("could not read local supabase keys")
    return {"url": url, "anon": anon, "service": service}


def _make_user(stack: dict, tag: str) -> str:
    """Create a confirmed user via the admin API; return a signed-in JWT."""
    email = f"it-{tag}-{uuid.uuid4().hex[:8]}@test.local"
    password = "integration-test-pw-1"
    admin = {"apikey": stack["service"], "Authorization": f"Bearer {stack['service']}"}
    r = httpx.post(f"{stack['url']}/auth/v1/admin/users", headers=admin,
                   json={"email": email, "password": password, "email_confirm": True})
    assert r.status_code in (200, 201), r.text
    r = httpx.post(f"{stack['url']}/auth/v1/token?grant_type=password",
                   headers={"apikey": stack["anon"]},
                   json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _ledger(stack: dict, jwt: str) -> Ledger:
    client = httpx.AsyncClient(
        base_url=stack["url"],
        headers={"apikey": stack["anon"], "Authorization": f"Bearer {jwt}"},
        timeout=30,
    )
    return Ledger(jwt, client=client)


def _recipient() -> str:
    return f"target-{uuid.uuid4().hex[:10]}@example.com"


def test_claim_race_exactly_one_winner(stack):
    """THE keystone test: 20 simultaneous claims admit exactly one winner."""
    jwt = _make_user(stack, "race")
    recipient = _recipient()

    async def main() -> list[str]:
        led = _ledger(stack, jwt)
        try:
            return list(await asyncio.gather(*(
                led.claim("email", recipient, skill="it", run_id="race-run")
                for _ in range(20)
            )))
        finally:
            await led.aclose()

    results = asyncio.run(main())
    assert results.count("claimed") == 1, results
    assert results.count("skipped") == 19, results


def test_two_person_overlap_zero_duplicates(stack):
    """Spec §7 scenario: A and X, different people, overlapping lists, no
    coordination — the union is claimed exactly once."""
    jwt_a, jwt_x = _make_user(stack, "personA"), _make_user(stack, "personX")
    shared = [_recipient() for _ in range(10)]
    only_a = [_recipient() for _ in range(5)]
    only_x = [_recipient() for _ in range(5)]

    async def run(jwt: str, recipients: list[str], run_id: str) -> list[str]:
        led = _ledger(stack, jwt)
        try:
            return list(await asyncio.gather(*(
                led.claim("email", r, skill="it", run_id=run_id) for r in recipients
            )))
        finally:
            await led.aclose()

    async def both():
        return await asyncio.gather(
            run(jwt_a, only_a + shared, "run-a"),
            run(jwt_x, shared + only_x, "run-x"),
        )

    res_a, res_x = asyncio.run(both())
    total_claimed = res_a.count("claimed") + res_x.count("claimed")
    assert total_claimed == len(shared) + len(only_a) + len(only_x), (res_a, res_x)
    # each shared recipient was claimed exactly once across BOTH people
    shared_claims = [a for a, _ in zip(res_a[len(only_a):], shared, strict=False)]
    shared_claims_x = res_x[: len(shared)]
    for ca, cx in zip(shared_claims, shared_claims_x, strict=True):
        assert {ca, cx} == {"claimed", "skipped"}, (ca, cx)


def test_suppression_blocks_even_forced_claims(stack):
    jwt = _make_user(stack, "sup")
    recipient = _recipient()

    async def main():
        led = _ledger(stack, jwt)
        try:
            await led.suppress("email", recipient, reason="opt-out")
            assert await led.claim("email", recipient) == "suppressed"
            assert await led.force_claim("email", recipient) == "suppressed"
            assert await led.check("email", recipient) == "suppressed"
        finally:
            await led.aclose()

    asyncio.run(main())


def test_mark_sent_and_check(stack):
    jwt = _make_user(stack, "mark")
    recipient = _recipient()

    async def main():
        led = _ledger(stack, jwt)
        try:
            assert await led.claim("email", recipient, run_id="r1") == "claimed"
            await led.mark_sent("email", recipient, message_hash="abc123")
            assert await led.check("email", recipient) == "contacted"
        finally:
            await led.aclose()

    asyncio.run(main())


def test_rls_cannot_read_others_contacted(stack):
    jwt_a, jwt_b = _make_user(stack, "rlsA"), _make_user(stack, "rlsB")
    recipient = _recipient()

    async def main():
        led_a = _ledger(stack, jwt_a)
        try:
            assert await led_a.claim("email", recipient) == "claimed"
        finally:
            await led_a.aclose()

    asyncio.run(main())
    # B selects the contacted table directly: must NOT see A's row…
    r = httpx.get(f"{stack['url']}/rest/v1/contacted",
                  params={"recipient": f"eq.{recipient}", "select": "recipient"},
                  headers={"apikey": stack["anon"], "Authorization": f"Bearer {jwt_b}"})
    assert r.status_code == 200 and r.json() == [], r.text
    # …and direct INSERT into contacted is impossible for clients (no policy).
    r = httpx.post(f"{stack['url']}/rest/v1/contacted",
                   headers={"apikey": stack["anon"], "Authorization": f"Bearer {jwt_b}"},
                   json={"channel": "email", "recipient": "x@y.z", "status": "sent",
                         "sent_by": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code in (401, 403), r.text


def test_reaper_releases_dead_runs_keeps_paused(stack):
    jwt = _make_user(stack, "reap")
    dead_r, paused_r = _recipient(), _recipient()

    async def main():
        led = _ledger(stack, jwt)
        try:
            # paused run: heartbeat says 'paused' → claims survive the reaper
            assert await led.claim("email", paused_r, run_id="run-paused") == "claimed"
            await led.heartbeat("run-paused", "it", "paused")
            # dead run: marked failed → claims are released
            assert await led.claim("email", dead_r, run_id="run-dead") == "claimed"
            await led.heartbeat("run-dead", "it", "failed")
            released = await led.release_stale_claims()
            assert released >= 1
            assert await led.claim("email", dead_r, run_id="run-new") == "claimed"  # released
            assert await led.claim("email", paused_r, run_id="run-new") == "skipped"  # kept
        finally:
            await led.aclose()

    asyncio.run(main())
