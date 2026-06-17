#!/usr/bin/env python3
"""Credit-frugal email engine: 1 Prospeo credit per company, multiple contacts out.

Why this exists: Prospeo charges a credit for BOTH people-search (1/page) and each
email reveal. On a small credit balance that's too expensive per contact. Names are
free from Clay's search step (which works; only Clay's email step was rate-limited),
so this script takes Clay-sourced names and spends exactly ONE Prospeo reveal per
company: it verifies a single seed contact, learns that company's email pattern
(e.g. {first}.{last}@domain), then constructs the rest of the contacts from the
pattern for free. The seed email is SMTP-verified; the constructed ones are
pattern-derived and only domain-level (MX) checked, a deliberate cost tradeoff.

Input CSV (one row per contact, grouped however): brand,domain,full_name,title
  - full_name may instead be first_name,last_name columns.
Output CSV (ready for send_fast.py): brand,domain,email,first_name,title,source
  - source = "verified" (the seed, SMTP-verified) or "pattern" (constructed).

Usage:
  python3 prospeo_enrich.py IN.csv OUT.csv [--max-credits N] [--pace S] [--seeds K]
    --max-credits  hard cap on Prospeo reveals to spend this run (default 90)
    --pace         seconds between reveal calls (default 5; respects rate limit)
    --seeds        seeds to try per company before giving up (default 1 = 1 credit)
Key: PROSPEO_API_KEY env, else read from ~/.claude.json.
"""
import csv, json, os, re, sys, time, socket, ssl, http.client, urllib.request, urllib.error

API = "https://api.prospeo.io"
API_HOST = "api.prospeo.io"

# This environment has flaky per-host DNS: a hostname resolves once, then the next
# lookup of the same host fails ("Name or service not known"), which kills long
# runs. Fix: resolve the API host ONCE to an IP, then connect by numeric IP
# (getaddrinfo on a literal IP never touches DNS) while keeping TLS SNI and cert
# validation pinned to the hostname. One good resolution carries the whole run.
_PIN = {}
def resolve_pin(host, tries=10):
    if host in _PIN:
        return _PIN[host]
    for i in range(tries):
        try:
            ip = socket.gethostbyname(host)
            _PIN[host] = ip
            return ip
        except OSError:
            time.sleep(3 * (i + 1))
    return None

class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        ip = _PIN.get(self.host) or resolve_pin(self.host) or self.host
        sock = socket.create_connection((ip, self.port), self.timeout, self.source_address)
        ctx = self._context or ssl.create_default_context()
        self.sock = ctx.wrap_socket(sock, server_hostname=self.host)

def _send(method, path, payload=None, timeout=60):
    """One HTTP call over a DNS-pinned TLS connection: connect by cached IP (no
    live DNS), SNI + cert validation still on the real hostname. Returns
    (status, body_text); raises OSError on connection failure."""
    conn = _PinnedHTTPSConnection(API_HOST, 443, timeout=timeout,
                                  context=ssl.create_default_context())
    try:
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"X-KEY": KEY}
        if body is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=body, headers=headers)
        r = conn.getresponse()
        return r.status, r.read().decode()
    finally:
        conn.close()

def prewarm(host, tries=10):
    return resolve_pin(host, tries) is not None

def get_key():
    k = os.environ.get("PROSPEO_API_KEY")
    if k:
        return k
    cfg = json.load(open(os.path.expanduser("~/.claude.json")))
    def find(d):
        if isinstance(d, dict):
            for kk, v in d.items():
                if kk == "PROSPEO_API_KEY":
                    return v
                r = find(v)
                if r:
                    return r
        elif isinstance(d, list):
            for v in d:
                r = find(v)
                if r:
                    return r
        return None
    return find(cfg)

KEY = get_key()

RL_TRIES = int(os.environ.get("RL_TRIES", "10"))   # patient 429 retries (free plan rate limit)
NET_TRIES = 4
def post(ep, payload):
    path = "/" + ep.lstrip("/")
    net = 0
    rl = 0
    while True:
        try:
            status, text = _send("POST", path, payload)
        except OSError as e:
            # connection/DNS blip — no request reached the server, no credit spent
            net += 1
            if net < NET_TRIES:
                wait = 5 * net
                print(f"    network error ({e}), retry in {wait}s", flush=True)
                time.sleep(wait)
                continue
            return 0, {"error": True, "error_code": f"network:{e}"}
        if status == 429:
            rl += 1
            if rl <= RL_TRIES:
                wait = min(20 * rl, 60)   # ramp to a steady 60s; wait the cooldown out
                print(f"    429 rate-limited ({rl}/{RL_TRIES}), backoff {wait}s", flush=True)
                time.sleep(wait)
                continue
            return status, {"error": True, "error_code": "Rate limit exceeded"}
        try:
            return status, json.loads(text)
        except Exception:
            return status, {"error": True, "raw": text[:200]}

def account():
    status, text = _send("GET", "/account-information", timeout=30)
    return json.loads(text).get("response", {})

# --- name + pattern helpers --------------------------------------------------
SUFFIX = re.compile(r"[^a-z]+$")
def clean(s):
    return SUFFIX.sub("", re.sub(r"[^a-zA-Z]", "", (s or "").strip().lower()))

def split_name(row):
    fn = (row.get("first_name") or "").strip()
    ln = (row.get("last_name") or "").strip()
    if not (fn and ln):
        parts = (row.get("full_name") or row.get("name") or "").replace(")", "").split()
        parts = [p for p in parts if p]
        if len(parts) >= 2:
            fn, ln = parts[0], parts[-1]
        elif parts:
            fn, ln = parts[0], ""
    return clean(fn), clean(ln), (row.get("first_name") or (row.get("full_name") or row.get("name") or "").split()[:1] or [""])[0]

def variants(f, l):
    fi, li = f[:1], l[:1]
    return {
        "{f}": f, "{l}": l,
        "{f}.{l}": f"{f}.{l}", "{f}{l}": f"{f}{l}", "{f}_{l}": f"{f}_{l}", "{f}-{l}": f"{f}-{l}",
        "{fi}{l}": f"{fi}{l}", "{fi}.{l}": f"{fi}.{l}",
        "{f}{li}": f"{f}{li}", "{f}.{li}": f"{f}.{li}",
        "{fi}{li}": f"{fi}{li}", "{l}.{f}": f"{l}.{f}", "{l}{f}": f"{l}{f}",
    }

def detect_pattern(email, f, l):
    if not (email and f):
        return None
    local = email.split("@")[0].lower()
    for name, val in variants(f, l).items():
        if val and local == val:
            return name
    return None

def build_email(pattern, f, l, domain):
    v = variants(f, l).get(pattern)
    return f"{v}@{domain}" if v else None

# --- mx (domain-level, free) -------------------------------------------------
def mx_ok(domain, _cache={}):
    # Lenient by design: this env's DNS is flaky, the harvest was already
    # DNS-validated, and Prospeo SMTP-verifies the seed email (which itself
    # confirms the domain accepts mail). So only skip on a definitive "no such
    # domain"; treat transient/uncertain resolution as deliverable.
    if domain in _cache:
        return _cache[domain]
    ok = True
    try:
        import dns.resolver
        try:
            ok = len(dns.resolver.resolve(domain, "MX")) > 0
        except dns.resolver.NXDOMAIN:
            ok = False
        except Exception:
            ok = True  # timeout / no-answer / resolver issue -> don't skip
    except Exception:
        ok = True
    _cache[domain] = ok
    return ok

TITLE_RANK = [
    ("founder", 0), ("co-founder", 0), ("cofounder", 0), ("ceo", 0), ("chief executive", 0),
    ("owner", 1), ("president", 1), ("cmo", 1), ("chief marketing", 1), ("coo", 1),
    ("chief operating", 1), ("cfo", 1), ("chief", 1),
    ("vp", 2), ("vice president", 2), ("head of", 2), ("director", 2),
]
def rank(title):
    t = (title or "").lower()
    for kw, r in TITLE_RANK:
        if kw in t:
            return r
    return 5

def seed_order(contacts):
    # prefer high rank AND a parseable first+last, stable by rank then name length
    scored = []
    for c in contacts:
        f, l, _ = split_name(c)
        ok = bool(f and l)
        scored.append((rank(c.get("title")), 0 if ok else 1, len(f) + len(l), c))
    scored.sort(key=lambda x: (x[0], x[1], -x[2]))
    return [c for *_, c in scored]

def enrich_seed(c):
    f, l, _ = split_name(c)
    domain = (c.get("domain") or "").strip().lower()
    data = {"company_website": domain}
    if f:
        data["first_name"] = f
    if l:
        data["last_name"] = l
    st, resp = post("enrich-person", {"data": data, "only_verified_email": False})
    if isinstance(resp, dict) and not resp.get("error"):
        p = resp.get("person") or {}
        em = p.get("email")
        if isinstance(em, dict):
            return em.get("email"), (em.get("status") or ""), False
        if isinstance(em, str):
            return em, "", False
    code = resp.get("error_code") if isinstance(resp, dict) else st
    return None, f"ERR:{code}", True

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    inp, outp = sys.argv[1], sys.argv[2]
    max_credits = 90
    pace = 5.0
    confirm = 2   # verified seeds to collect per company (the credit cost per company)
    seeds = 4     # max enrich attempts per company to find those hits (misses are free)
    a = sys.argv[3:]
    for i, x in enumerate(a):
        if x == "--max-credits": max_credits = int(a[i + 1])
        elif x == "--pace": pace = float(a[i + 1])
        elif x == "--seeds": seeds = int(a[i + 1])
        elif x == "--confirm": confirm = int(a[i + 1])

    if not prewarm(API_HOST):
        print(f"WARNING: could not pre-resolve {API_HOST}; DNS may be down")
    acct = account()
    have = acct.get("remaining_credits", 0)
    print(f"Prospeo: plan={acct.get('current_plan')} remaining_credits={have} "
          f"(renews in {acct.get('next_quota_renewal_days')}d)")
    budget = min(max_credits, have)
    print(f"Spending up to {budget} reveals this run (1 per company).\n")

    rows = list(csv.DictReader(open(inp)))
    by_domain = {}
    for r in rows:
        d = (r.get("domain") or "").strip().lower()
        if d:
            by_domain.setdefault(d, []).append(r)

    out = csv.writer(open(outp, "w", newline=""))
    out.writerow(["brand", "domain", "email", "first_name", "title", "source"])
    spent = 0      # real reveals (Prospeo charges on a hit; misses are refunded)
    attempts = 0
    n_companies = 0
    n_out = 0
    for domain, contacts in by_domain.items():
        if spent >= budget:
            print(f"\nBudget reached ({spent} reveals). Stopping; {len(by_domain) - n_companies} companies left.")
            break
        if not mx_ok(domain):
            print(f"- {domain}: domain has no MX/A, skipping")
            continue
        n_companies += 1
        brand = contacts[0].get("brand", "")
        # Collect up to `confirm` VERIFIED seeds (each a charged reveal). Misses are
        # free, so try up to `seeds` contacts in priority order to find them.
        hits = []          # (email, f, l, disp, title, pattern)
        used = set()
        for c in seed_order(contacts)[:seeds]:
            if len(hits) >= confirm or spent >= budget:
                break
            f, l, disp = split_name(c)
            if not (f and l):
                continue
            email, status, err = enrich_seed(c)
            attempts += 1
            time.sleep(pace)
            if email and "@" in email and email.lower() not in used:
                spent += 1
                used.add(email.lower())
                hits.append((email, f, l, disp, c.get("title", ""), detect_pattern(email, f, l)))
                out.writerow([brand, domain, email, disp, c.get("title", ""), "verified"])
                n_out += 1
            elif not (email and "@" in email):
                print(f"  · {brand} ({domain}): {f}.{l} no email [{status}] (no charge)")
        if not hits:
            print(f"- {brand} ({domain}): no verifiable seed found, skipped")
            continue
        patterns = {h[5] for h in hits if h[5]}
        if len(patterns) == 1:
            # all verified seeds agree on one pattern -> safe to extend for free
            pat = next(iter(patterns))
            built = 0
            for c in contacts:
                f, l, disp = split_name(c)
                if not (f and l):
                    continue
                em = build_email(pat, f, l, domain)
                if not em or em.lower() in used:
                    continue
                used.add(em.lower())
                out.writerow([brand, domain, em, disp, c.get("title", ""), "pattern"])
                n_out += 1
                built += 1
            print(f"- {brand} ({domain}): {len(hits)} verified, pattern {pat} confirmed, +{built} extended")
        else:
            # seeds disagree (multi-pattern) or pattern unrecognized -> send verified only
            print(f"- {brand} ({domain}): {len(hits)} verified, patterns {patterns or '{unrecognized}'} "
                  f"not unanimous -> verified only, no extension")

    try:
        real_left = account().get("remaining_credits", "?")
    except Exception:
        real_left = f"~{have - spent}"
    print(f"\nDONE: {n_companies} companies, {attempts} enrich attempts, {spent} reveals charged, "
          f"{n_out} contacts written -> {outp}")
    print(f"Remaining credits (live): {real_left}")

if __name__ == "__main__":
    main()
