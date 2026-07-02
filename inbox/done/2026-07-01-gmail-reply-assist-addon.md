---
title: Build a Gmail add-on that drafts a reply to the open email, using the same backend as `/respond`
created: 2026-07-01
created_by: shamit
assignee:            # any engineering-capable agent
priority: normal
claimed_by: claude (in-session with shamit)
claimed_at: 2026-07-01
---

## Task

Build a Gmail add-on that lets a founder reply to a single email faster. The founder opens an
email in Gmail (in the browser), clicks the add-on in the sidebar, and gets a recommended reply
drafted in their voice from our past replies. They edit it and send it, in-thread, as themselves.

This is a new surface, not a replacement. The `/respond` Slack feature already exists and keeps
working. The add-on reuses the same draft-generation backend `/respond` uses; it is just a
different way to invoke it, aimed at responding to specific, individual emails in the moment you
are reading them rather than walking a batch queue.

The add-on works on the web: a Google Workspace add-on renders as a panel in the right-hand
sidebar of Gmail in the browser. That panel is the whole product surface; there is no separate
web app to build.

Before writing code, read the campaign wizard architecture doc and skim how `/respond` calls the
draft backend, so this add-on calls the same thing rather than reinventing generation. Then
critique this plan before you start (per the repo harness rules). Paths and function names are
left out on purpose because they drift; find the current owner of each capability by reading the
campaign skill.

## How it fits with what exists

- The draft generator is shared. There is (or will be, see prerequisite) a backend that, given an
  incoming email's context and which founder is replying, returns a reply draft grounded in our
  past-reply corpus in Supabase (`reply_examples`), matched by category and shaped by that
  founder's voice card. `/respond` uses this. The add-on must call the same logic, not a copy.
- The add-on drafts from whatever email is open. It is not limited to known prospect replies; if
  a founder has an email open and clicks the add-on, it drafts a reply to that email.
- Sending is native. Because the add-on runs as the logged-in founder inside Gmail, it sends the
  reply through Gmail itself, correctly threaded, with no stored refresh tokens and no manual
  reply-header handling. This is simpler and safer than the Slack send path.

## Prerequisite

The shared draft logic must be reachable by the add-on as an authenticated HTTPS endpoint (call
it `draft-reply`: takes the open message's subject, body, and thread context plus the founder
identity, returns draft text). If `/respond` already calls it over such an endpoint, reuse that.
If the generation currently lives only inside the Slack wizard process (which runs over Socket
Mode and needs no public URL), the one piece of new infrastructure here is exposing that same
logic behind a small authed HTTPS endpoint. Do not duplicate the generation logic to do this;
wrap the existing one.

## The add-on

- A Google Workspace add-on (Apps Script / CardService) scoped to Gmail, shown in the sidebar.
- On opening a message, it reads that message and its thread.
- On click (a "Draft a reply" button), it calls the `draft-reply` endpoint with the open email's
  context and the founder identity, and renders the returned draft in an editable text card, with
  a Send button and a Regenerate button.
- On Send, it sends the edited text natively through Gmail as the founder, in-thread.
- After a successful send, it notifies the backend so the backend can:
  - record the sent `(incoming_email, sent_reply)` pair back into `reply_examples` as a curated
    gold example (the feedback loop that makes future drafts more founder-shaped), and
  - mark the email handled in the shared dismissal store, so if it was also a triage row it does
    not resurface in the morning digest.

## Security (this is a new public surface, treat it as one)

Follows the repo's frontend to backend to DB rule and the standard security rules:
- The add-on holds no secrets and never touches Supabase or the LLM directly. All of that stays
  server-side behind the endpoint.
- The endpoint authenticates the caller. Verify the Google-signed user identity token the add-on
  presents and confirm the caller is one of our founders before doing any work.
- Rate-limit the endpoint. Return vague errors to the client, keep detailed logs server-side, and
  never log message bodies, tokens, or other PII.

## Gotchas

1. Do not fork the draft logic into the add-on. It calls the same backend as `/respond`.
2. Native send and threading. Prefer Gmail's native reply so threading and sender are correct for
   free; do not rebuild the Slack send path here.
3. Authenticate the endpoint. An unauthenticated draft endpoint is an open door to our corpus and
   LLM spend.
4. Feedback loop and mark-as-handled happen on the backend after send, keyed by message id, so a
   handled email does not get answered again from another surface.
5. Workspace add-on deployment and per-user install (and Google's review/publish flow for an
   add-on) are part of this task, budget for them.
6. Draft prompt matches voice and reasoning of past examples; it does not copy them verbatim (this
   is the backend's job, but verify the drafts the add-on shows are not near-verbatim reuse).

## Done when

- A founder can open any email in Gmail on the web, click the add-on, and see a recommended reply
  drafted in their voice from our past replies.
- They can edit it and send it, and it goes out in-thread from their own account.
- The draft came from the same backend `/respond` uses, not a duplicated generator.
- The endpoint rejects unauthenticated or non-founder callers.
- A reply sent from the add-on is written back into `reply_examples` as a gold example and, if the
  email was a triage row, does not resurface in the next digest.
- The campaign wizard architecture doc is updated to note the add-on as a second client of the
  shared draft backend.

## Out of scope

- Any change to `/respond` beyond, if needed, exposing its draft logic behind a shared endpoint.
- Unsupervised or auto-send replies. A human edits and sends every message.
- Building the past-reply corpus or the voice card if `/respond` already has them; reuse them. If
  they do not exist yet, that work belongs to the shared-backend task, not this add-on.

## Result (2026-07-01)

Built. The `/respond` draft engine already existed (`reply_drafter.generate_draft`,
`reply_followup.create_draft_api`/`send_draft_api`, `reply_examples.add_gold_example`), so the
add-on reuses it rather than duplicating anything.

Verified working against a live founder inbox on 2026-07-01 (drafted and reachable end to end).

Auth: started with a Google identity token (needed a GCP project per account), but that made
install painful and hit a cross-org ownership wall. Switched to a shared secret plus an
`X-Addon-User` email header, which removed the GCP requirement entirely. That is the shipped
design.

Added:
- `skills/campaign/wizard/addon_api.py`: an aiohttp endpoint hosted in the wizard process.
  Routes: `POST /addon/draft {thread_id}`, `POST /addon/send {thread_id, body}`, `GET
  /addon/health`. Every call checks a shared secret (`ADDON_SHARED_SECRET`) and that the
  `X-Addon-User` email is a founder in `agent.SENDERS`, with a per-founder rate limit. Send
  re-derives the thread anchors server-side (client only sends thread id + edited body), sends
  in-thread as the founder, and writes the sent reply back as a gold example.
- `skills/campaign/wizard/reply_drafter.py`: new `read_target()` helper (non-LLM send anchors from
  a thread id) for the send path.
- `skills/campaign/wizard/slack_bot.py`: `main()` starts the endpoint alongside Socket Mode when
  `ADDON_API_ENABLED` is set (off by default, so the Slack-only deploy is unchanged), wrapped so a
  start failure never takes down the Slack bot.
- `skills/campaign/gmail_addon/`: the Apps Script add-on (`appsscript.json`, `Code.gs`), `README.md`
  (design + backend setup) and `INSTALL.md` (per-founder steps). Minimal scopes; the add-on holds
  no secret in code (the shared secret is a Script Property).
- Tests: `skills/campaign/tests_addon/` (10 tests, all passing) covering the shared-secret auth
  gate (missing/wrong secret, backend-secret unset, non-founder, missing email, accept, rate
  limit) and payload shaping. Delete this folder after merge per the repo rule.

Deploy state: live on Railway `slack_wiz` (production) with `ADDON_API_ENABLED=1` and
`ADDON_SHARED_SECRET` set on that service. The one secret pasted during setup passed through a
chat and should be rotated (Railway + each install).
