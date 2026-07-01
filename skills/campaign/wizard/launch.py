"""Entry point for the Slack campaign wizard.

Railway runs this image as the slack_wiz service. The former Telegram front end
was removed; the team uses Slack only. WIZARD_PLATFORM is no longer read.
"""
import asyncio

from . import slack_bot

asyncio.run(slack_bot.main())
