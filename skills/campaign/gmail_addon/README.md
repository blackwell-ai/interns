# Blackwell Reply Assist (Gmail add-on)

A Gmail sidebar add-on that drafts a reply to the email you have open, in your voice,
from our past replies. It is a second front door to the same draft engine the Slack
`/respond` command uses. It replaces nothing.

You open an email in Gmail on the web, click the add-on, get a recommended reply, edit
it, and send. The reply goes out in-thread, as you.

For per-founder install steps, see `INSTALL.md`.

## How it fits together

```
Gmail add-on (this folder, Apps Script)
      |  POST /addon/draft {thread_id}
      |  POST /addon/send  {thread_id, body}
      |  headers: Authorization: Bearer <shared secret>, X-Addon-User: <your email>
      v
addon_api.py  (aiohttp endpoint in the wizard process)
      |  checks the shared secret + that X-Addon-User is a founder, then reuses:
      |    reply_drafter.generate_draft / read_target
      |    reply_followup.create_draft_api + send_draft_api
      |    reply_examples.add_gold_example   (feedback loop)
      v
Gmail API + Supabase reply_examples corpus
```

The add-on does all the drafting, sending, Supabase access, and LLM calls server-side
behind the endpoint. It authenticates with a shared secret (proving the request came
from our add-on) plus the signed-in user's email, which must be one of the three
founders. This is deliberately simple: an internal tool for three people, with no
GCP-linked identity token to set up.

## Auth model

- The add-on reads the shared secret from its Script Property `ADDON_SHARED_SECRET` and
  sends it as `Authorization: Bearer <secret>`. It also sends the signed-in email as
  `X-Addon-User` (from `Session.getEffectiveUser().getEmail()`).
- The backend compares the secret against its `ADDON_SHARED_SECRET` env var and maps the
  email to a founder in `agent.SENDERS`. Both must pass, then it rate-limits per founder.
- The same secret value is shared by all installers. If it leaks, rotate it on Railway
  and in each install.

## Backend setup

The endpoint lives in `skills/campaign/wizard/addon_api.py` and is off by default. On the
Railway `slack_wiz` service (production environment):

- `ADDON_API_ENABLED=1` so `slack_bot.main()` starts the HTTP server alongside Socket
  Mode.
- `ADDON_SHARED_SECRET=<a random string>` (letters, numbers, `-`, `_`; avoid quotes,
  commas, spaces). This must match the value each install puts in its Script Property.
- The server binds `PORT` (Railway sets and routes to it automatically), falling back to
  `ADDON_PORT` or 8080. Expose the service so it has a public HTTPS domain; that domain
  is the backend URL baked into `Code.gs` / `appsscript.json`.
- Existing env the reused code already needs: `GMAIL_REFRESH_TOKEN_{ARMAAN,SAMARJIT,
  ETHAN}`, `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`.

Health check: `GET /addon/health` returns `{"ok": true}`.

Important: Railway variables are scoped per service and per environment. Set
`ADDON_SHARED_SECRET` on the `slack_wiz` service in the `production` environment, not as a
project-level shared variable, or the backend will not see it and every call returns 401.

## Scopes and why

- `gmail.addons.current.message.readonly`: read only the message you have open (to get
  its thread id). No broad mailbox access.
- `script.external_request`: call our backend.
- `userinfo.email`: read your own email to send as `X-Addon-User`.
- `gmail.addons.execute`: run as a Gmail add-on.

The add-on does not request send/compose scope: the backend sends via the founder's
stored credentials, the same path `/respond` uses, so threading and sender are correct.

## Notes

- Drafts come from the shared engine, so they reflect the founder's voice card and past
  replies, and every reply sent from here is written back as a gold example.
- Because the backend sends and the corpus write-back is keyed by message, a thread you
  answer here naturally drops out of the next `/respond` and morning triage (you replied
  last, so it is no longer awaiting you).
- Cross-org note: the founders span two Google orgs (dartmouth.edu, berkeley.edu). Each
  founder creates their own script in their own account (see `INSTALL.md`); do not share
  or transfer one script across accounts, which is what the org boundary blocks.
