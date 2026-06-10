#!/usr/bin/env python3
"""One batch of autonomous cold sends.

Input: a batch CSV (brand,domain,email,first_name,title,company_blurb).
Per row: suppression CLAIM (insert; conflict -> skip) -> personalization hook
via headless Claude Code -> send via gog (CC co-founders) -> update reason.
Prints a per-row status line and a summary; exits 9 on gmail hard-quota.
"""
import csv, json, os, re, subprocess, sys, time, urllib.request, urllib.error

ACC = "armaan.priyadarshan.29@dartmouth.edu"
CC = "samarjit.deshmukh.29@dartmouth.edu,ethanpzhou@berkeley.edu,shamitd@stanford.edu"
SUBJECT = "Stanford Student Question - thoughts on AI retail tools"
SUPA = os.environ["SUPABASE_URL"] + "/rest/v1/suppression"
KEY = os.environ["SUPABASE_SECRET_KEY"]
LOG = "/tmp/autonomous_send_log.csv"

def supa(method, url, payload=None, headers=None):
    h = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                                 method=method, headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def claim(email, brand):
    # insert = claim; 409/conflict -> someone (or a past run) already has it
    status, body = supa("POST", SUPA, [{"channel": "email", "recipient": email,
        "reason": f"CLAIMED autonomous run 2026-06-10: {brand}"}],
        {"Prefer": "return=minimal"})
    return status in (200, 201)

def update_reason(email, reason):
    supa("PATCH", f"{SUPA}?channel=eq.email&recipient=eq.{urllib.parse.quote(email)}",
         {"reason": reason}, {"Prefer": "return=minimal"})

def hook(brand, domain, blurb):
    prompt = (f"Brand: {brand} ({domain}). What we know: {blurb or 'a DTC e-commerce brand'}.\n"
        "Write ONE sentence (max 25 words) for a cold email to this brand's founder, "
        "pointing out something specific about how their multichannel/online setup likely "
        "appears to AI shopping assistants (ChatGPT etc). Concrete, plain, no flattery, no jargon, "
        "no quotes around the output. It must read naturally after the sentence: "
        "\"We're Stanford/Dartmouth students curious how {brand} is thinking about AI, "
        "given 50 million people now shop with ChatGPT daily.\"")
    p = subprocess.run(["claude", "-p", "--output-format", "json", "--model", "claude-haiku-4-5",
                        "--system-prompt", "You write one precise sentence. Output only the sentence.",
                        "--tools", "", "--no-session-persistence"],
                       input=prompt, capture_output=True, text=True, timeout=120,
                       env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"},
                       cwd="/tmp")
    if p.returncode != 0:
        return ""
    try:
        d = json.loads(p.stdout)
        s = (d.get("result") or "").strip().strip('"')
        return s if 8 < len(s) < 220 and "{" not in s else ""
    except Exception:
        return ""

def send(to, first_name, brand, hook_sentence):
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    body = f"""{greeting}

We're Stanford/Dartmouth students curious how {brand} is thinking about AI, given 50 million people now shop with ChatGPT daily. {hook_sentence}

Would you be open to a quick 10-minute call?

If not, we would appreciate even a one-sentence response with your thoughts on how retailers are improving their visibility with AI.

Thanks,
Armaan"""
    p = subprocess.run(["gog", "gmail", "send", "-a", ACC, "--to", to, "--cc", CC,
                        "--subject", SUBJECT, "--body", body, "--no-input"],
                       capture_output=True, text=True, timeout=120)
    out = (p.stdout + p.stderr)
    if p.returncode == 0 and "message_id" in out:
        mid = re.search(r"message_id\s+(\S+)", out)
        return "sent", mid.group(1) if mid else ""
    if any(s in out.lower() for s in ("quota", "rate limit", "ratelimit", "limit exceeded")):
        return "quota", out[:200]
    return "failed", out[:200]

def main(batch_csv):
    rows = list(csv.DictReader(open(batch_csv)))
    sent = skipped = failed = 0
    logf = open(LOG, "a", newline="")
    w = csv.writer(logf)
    for r in rows:
        email = r["email"].strip().lower()
        brand = r["brand"].strip()
        if not email or "@" not in email:
            continue
        if not claim(email, brand):
            print(f"SKIP (already claimed/suppressed): {email}")
            skipped += 1
            continue
        h = hook(brand, r["domain"], r.get("company_blurb", ""))
        if not h:
            h = "We're curious whether assistants recommending products in your category ever actually surface your store."
        status, detail = send(email, r.get("first_name", ""), brand, h)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        w.writerow([ts, email, brand, status, detail]); logf.flush()
        if status == "sent":
            update_reason(email, f"contacted 2026-06-10: blackwell autonomous cold email ({brand}; msg {detail})")
            print(f"SENT: {brand} <{email}> msg={detail}")
            sent += 1
        elif status == "quota":
            # release the claim so a future run can take it
            supa("DELETE", f"{SUPA}?channel=eq.email&recipient=eq.{urllib.parse.quote(email)}&reason=like.CLAIMED*", None,
                 {"Prefer": "return=minimal"})
            print(f"QUOTA HIT — stopping cleanly: {detail}")
            print(f"SUMMARY sent={sent} skipped={skipped} failed={failed}")
            sys.exit(9)
        else:
            update_reason(email, f"send FAILED 2026-06-10 ({brand}): {detail[:120]}")
            print(f"FAILED: {email}: {detail}")
            failed += 1
        time.sleep(25)
    print(f"SUMMARY sent={sent} skipped={skipped} failed={failed}")

if __name__ == "__main__":
    main(sys.argv[1])
