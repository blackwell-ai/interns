"""Scheduled morning jobs, run by APScheduler (wired up in `slack_bot.main()`):
the 9am morning follow-ups and the daily inbox-triage broadcast.

The evening run-campaigns nudge and the pester loop live in `slack_bot.py`
instead, next to `main()` which schedules them, because their tests patch
`slack_bot._post_channel` and the nudge functions must resolve that name from
the `slack_bot` module. The reply helper `_post_channel` and the shared pester
counter live in `session.py`; `blocks.py` draws the morning report.
"""
import logging
import os

from skills.campaign import reply_followup

from . import blocks, gmail_auth, slack_config, triage
from .session import _post_channel

log = logging.getLogger(__name__)


async def _daily_triage() -> None:
    """Scan the inboxes, post the tables, then ping the team. Called at the tail of
    the morning follow-up job so the report is followed by the triage."""
    try:
        await _post_channel(":scroll: Running the daily inbox triage...")
        for m in await triage.run_triage(_post_channel):
            await _post_channel(m["text"], m.get("blocks"))
        await _post_channel("<!channel> these are today's replies worth handling. "
                            "Please take the ones owned by your account.")
        log.info("Daily triage broadcast sent")
    except Exception:
        log.exception("daily triage failed")
        await _post_channel("The morning triage faltered. Check the logs.")


# The sender mailboxes the morning pass scans and sends from (those with a stored
# refresh token on the server).
_FOLLOWUP_ACCOUNTS = list(gmail_auth._SENDER_REFRESH_KEYS.keys())


async def _morning_followups() -> None:
    """9am Pacific: for each sender, auto-send due out-of-office bumps, hold future
    ones as drafts to send on the day, and stage redirect drafts for approval. Post
    the report, then run the inbox triage so it follows right after."""
    if not slack_config.SLACK_FOLLOWUP_ENABLED:
        await _daily_triage()
        return
    # The contacted ledger is team-wide; read it with the service-role key so the
    # redirect dedup sees every teammate's sends, not just the bot's rows.
    os.environ["TRIAGE_LEDGER_SERVICE_KEY"] = os.environ.get("SUPABASE_SECRET_KEY", "")
    await _post_channel(":sunrise: Running the morning follow-ups...")
    results = []
    for account in _FOLLOWUP_ACCOUNTS:
        try:
            res = await reply_followup.run_morning(
                account, get_token=gmail_auth.get_access_token, auto_send=True)
            results.append(res)
        except Exception as e:  # noqa: BLE001 - one bad account must not stop the rest
            log.exception("morning follow-ups failed for %s", account)
            results.append({"account": account, "sent": [], "scheduled": [],
                            "redirect_drafts": [],
                            "errors": [{"note": account, "detail": str(e)[:150]}]})
    try:
        fallback, report_blocks = blocks._morning_report_blocks(results)
        await _post_channel(fallback, report_blocks)
    except Exception:
        log.exception("morning report render failed")
        await _post_channel("The morning follow-ups ran but the report failed to render.")
    # The report is followed by the triage tables.
    await _daily_triage()
