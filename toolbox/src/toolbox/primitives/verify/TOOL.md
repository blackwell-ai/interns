# verify — MX/DNS deliverability checks (no SMTP probes)

No connection needed. Checks null-MX (RFC 7505) and MX-or-A fallback (RFC 5321).

## verify.check
- in: contacts.csv → out: verified.csv (+`verified,mx_ok,verify_reason`)
- flags: `--concurrency 20`, `--drop-unverified/--keep-unverified` (default drop)
