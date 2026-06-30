import os

# Slack wizard configuration. The bot token (xoxb-) acts as the email_wizard app;
# the app-level token (xapp-) opens the Socket Mode WebSocket. Both come from the
# Slack app config and are injected as environment variables, never committed.
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

# The one public channel the wizard listens and replies in. The bot only acts on
# @mentions inside this channel and ignores everything else.
SLACK_CHANNEL_ID = os.environ["SLACK_CHANNEL_ID"]

# Scheduled jobs: the 5:30pm "run campaigns" nudge (repeats until a campaign
# runs) and the 10am inbox triage broadcast. On by default; set to a falsy value
# to disable. Times run in SLACK_SCHEDULE_TZ (Pacific).
SLACK_SCHEDULES_ENABLED = os.environ.get("SLACK_SCHEDULES_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
SLACK_SCHEDULE_TZ = os.environ.get("SLACK_SCHEDULE_TZ", "America/Los_Angeles")

# Slack user id to @-mention in the run-campaigns reminder (e.g. U0BD6S8V4LE).
SLACK_REMINDER_USER = os.environ.get("SLACK_REMINDER_USER", "")

# Daily send target. The run-campaigns nudge keeps pestering until this many
# emails have actually gone out today, so a small send does not silence it. The
# team's capacity is 3 senders x 800/day = 2400; default a bit under to "maxed".
SLACK_DAILY_TARGET = int(os.environ.get("SLACK_DAILY_TARGET", "2000"))

# The 9am morning pass: auto-send due out-of-office bumps, hold future ones, stage
# redirect drafts, then post the report followed by the triage tables. On by
# default; set falsy to disable the whole morning job (and its autonomous sends).
SLACK_FOLLOWUP_ENABLED = os.environ.get("SLACK_FOLLOWUP_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
