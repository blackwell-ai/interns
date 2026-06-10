#!/usr/bin/env python3
"""Fast volume sender — no LLM in the loop, proven template, rate-limit aware.

Per row (brand,domain,email,first_name):
  claim in suppression (insert; conflict -> skip) -> send via gog -> record.
No per-email personalization call (that was the slow part); uses the proven
"Stanford Student Question" template with {brand}/{first_name} substitution.
Paced PACE seconds/send; on a 403 rate-limit it backs off and retries the SAME
row (no skip, no double-send — the claim already happened once and send is
idempotent per claim). Exits 0 at end; the per-minute API cap is the ceiling.
"""
import csv, json, os, re, subprocess, sys, time, urllib.request, urllib.parse, urllib.error

ACC = "armaan.priyadarshan.29@dartmouth.edu"
CC = "samarjit.deshmukh.29@dartmouth.edu,ethanpzhou@berkeley.edu,shamitd@stanford.edu"
SUBJECT = "Stanford Student Question - thoughts on AI retail tools"
SUPA = os.environ["SUPABASE_URL"] + "/rest/v1/suppression"
KEY = os.environ["SUPABASE_SECRET_KEY"]
LOG = "/tmp/autonomous_send_log.csv"
PACE = float(os.environ.get("PACE", "6"))

def supa(method, url, payload=None, prefer="return=minimal"):
    h = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": prefer}
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                                 method=method, headers=h)
    try:
        with urllib.request.urlopen(req) as r: return r.status
    except urllib.error.HTTPError as e: return e.code

def claim(email, brand):
    return supa("POST", SUPA, [{"channel":"email","recipient":email,
        "reason":f"CLAIMED autonomous-volume 2026-06-10: {brand}"}]) in (200,201)

def update_reason(email, reason):
    supa("PATCH", f"{SUPA}?channel=eq.email&recipient=eq.{urllib.parse.quote(email)}", {"reason":reason})

def body_for(first_name, brand):
    greeting = f"Hi {first_name}," if first_name else "Hi there,"
    return f"""{greeting}

We're Stanford/Dartmouth students curious how {brand} is thinking about AI, given 50 million people now shop with ChatGPT daily.

Would you be open to a quick 10-minute call?

If not, we would appreciate even a one-sentence response with your thoughts on how retailers are improving their visibility with AI.

Thanks,
Armaan"""

def send(to, first_name, brand):
    p = subprocess.run(["gog","gmail","send","-a",ACC,"--to",to,"--cc",CC,
                        "--subject",SUBJECT,"--body",body_for(first_name,brand),"--no-input"],
                       capture_output=True, text=True, timeout=120)
    out = p.stdout + p.stderr
    if p.returncode == 0 and "message_id" in out:
        return "sent", (re.search(r"message_id\s+(\S+)", out) or [None,""])[1]
    if "ratelimit" in out.lower() or "rate limit" in out.lower() or "quota" in out.lower():
        return "ratelimit", ""
    return "failed", out[:150]

def process_row(r, counts, log):
    email = (r.get("email") or "").strip().lower(); brand = (r.get("brand") or "").strip()
    if "@" not in email: return
    if not claim(email, brand):
        counts["skipped"] += 1; return
    while True:
        status, detail = send(email, r.get("first_name",""), brand)
        if status != "ratelimit": break
        time.sleep(45)  # hold the claim, retry same recipient after cooldown
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    log.writerow([ts, email, brand, status, detail]);
    if status == "sent":
        update_reason(email, f"contacted 2026-06-10: blackwell volume cold email ({brand}; msg {detail})")
        counts["sent"] += 1
        if counts["sent"] % 10 == 0: print(f"... {counts['sent']} sent", flush=True)
    else:
        update_reason(email, f"send FAILED 2026-06-10 ({brand}): {detail[:100]}")
        counts["failed"] += 1
    time.sleep(PACE)

def main(path):
    """Daemon: re-scan the queue file forever; claim() dedups already-sent rows
    so re-scanning is safe. Exits after IDLE_CYCLES scans with no new sends so it
    doesn't run forever once the queue is drained and no longer being appended."""
    counts = {"sent": 0, "skipped": 0, "failed": 0}
    log = csv.writer(open(LOG, "a", newline=""))
    idle = 0
    IDLE_CYCLES = int(os.environ.get("IDLE_CYCLES", "20"))  # ~20 min of no new rows -> stop
    while idle < IDLE_CYCLES:
        before = counts["sent"]
        try:
            rows = list(csv.DictReader(open(path)))
        except FileNotFoundError:
            rows = []
        for r in rows:
            process_row(r, counts, log)
        if counts["sent"] == before:
            idle += 1; time.sleep(60)
        else:
            idle = 0
    print(f"SUMMARY sent={counts['sent']} skipped={counts['skipped']} failed={counts['failed']}", flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
