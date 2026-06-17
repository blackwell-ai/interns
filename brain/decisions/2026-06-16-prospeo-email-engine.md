# Decision: Prospeo is the volume email-finding engine (2026-06-16)

## Context

Cold-email volume needs verified decision-maker emails at scale. We had been
sourcing emails through the Clay claude.ai MCP connector. On 2026-06-15 that
path failed under load: after about 600 email reveals in a day, Clay's email
step returned "None Found" for everyone, including well-covered founders, while
its contact search kept working and the credit flag still read available.

Diagnosis (confirmed, not guessed): Clay finds emails via a waterfall of
third-party vendors (Hunter, Prospeo, Snov, and others) run on Clay's shared
managed accounts. The MCP connector rides that shared quota, can't be driven
headlessly, and exposes no per-vendor state. When the shared vendor quota is
spent or throttled, the waterfall short-circuits and every lookup renders as
"None Found", and because Clay refunds misses the credit flag never drops. So
the failure is invisible through the connector. See
[outreach-learnings](../research/outreach-learnings.md).

## Decision

Split the two jobs. Use Clay's contact SEARCH step for names and titles (it's
reliable and, with no email data point requested, free to us). Use Prospeo
directly over its REST API as the email-finding engine for volume. Keep Clay for
interactive, hand-picked, multi-contact work where its orchestration earns its
premium. Apollo was considered and rejected for the email step: its stored
database decays and bounces 15 to 38 percent, while on-demand finders verify
fresh; Apollo's API also needs the $119/seat Organization tier.

## How Prospeo is used

- REST base `https://api.prospeo.io`, header `X-KEY`. Key lives in `~/.claude.json`
  (the MCP registration), not in the repo. Endpoints: `/account-information`
  (free, shows `remaining_credits`), `/search-person` (1 credit/page),
  `/enrich-person` and `/bulk-enrich-person` (charge on a successful reveal;
  misses are refunded), `/search-suggestions` (free).
- Engine: `skills/autonomous-outreach/prospeo_enrich.py`. Input is Clay-sourced
  names grouped by company; output is the `brand,domain,email,first_name` CSV
  that `send_fast.py` already sends.
- Credit strategy (plan is small, ~100 credits/month): do NOT enrich every
  contact. Per company, verify a couple of seed contacts, learn the company's
  email pattern, and construct the rest for free. Because misses are refunded,
  the script tries several contacts until it gets the paid hits, so cost stays
  near the intended reveals per company.

## Caveats learned the hard way

- Companies are not single-pattern. Bellroy's CEO is `lina.calabria@` but its
  co-founder is `afallshaw@`. So pattern-extending from one seed mis-constructs
  some addresses. Mitigation chosen 2026-06-16: 2-credit mode (verify two seeds;
  extend only if their patterns agree, otherwise send only the two verified).
  Constructed (non-verified) addresses carry bounce risk; only seeds are
  SMTP-verified.
- This run environment has flaky per-host DNS: a host resolves once, then the
  next lookup of the same host fails ("Name or service not known"), which kills
  long runs. urllib's opener and a getaddrinfo cache did NOT reliably fix it.
  What works: resolve the API host once, then connect by numeric IP via a custom
  `http.client.HTTPSConnection` (SNI and cert validation still pinned to the
  hostname). Also: background bash tasks need `dangerouslyDisableSandbox` to have
  network at all, and long runs must be backgrounded (foreground auto-backgrounds).
