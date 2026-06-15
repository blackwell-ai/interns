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

# Sender + CC are env-parameterized so the same proven script runs from any
# co-founder's account (each CCs the other three). Defaults preserve the
# original Armaan-sent behavior.
ACC = os.environ.get("SEND_ACCOUNT", "armaan.priyadarshan.29@dartmouth.edu")
_COFOUNDERS = {
    "armaan.priyadarshan.29@dartmouth.edu": "Armaan",
    "samarjit.deshmukh.29@dartmouth.edu": "Samarjit",
    "ethanpzhou@berkeley.edu": "Ethan",
    "shamitd@stanford.edu": "Shamit",
}
CC = os.environ.get("SEND_CC") or ",".join(a for a in _COFOUNDERS if a != ACC)
SENDER_NAME = os.environ.get("SENDER_NAME") or _COFOUNDERS.get(ACC, "Armaan")
SUBJECT_TMPL = "Stanford Student Question About {brand}"
SUPA = os.environ["SUPABASE_URL"] + "/rest/v1/suppression"
KEY = os.environ["SUPABASE_SECRET_KEY"]
LOG = "/tmp/autonomous_send_log.csv"
PACE = float(os.environ.get("PACE", "6"))
TODAY = time.strftime("%Y-%m-%d")

def supa(method, url, payload=None, prefer="return=minimal"):
    h = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": prefer}
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                                 method=method, headers=h)
    try:
        with urllib.request.urlopen(req) as r: return r.status
    except urllib.error.HTTPError as e: return e.code

def claim(email, brand):
    return supa("POST", SUPA, [{"channel":"email","recipient":email,
        "reason":f"CLAIMED autonomous-volume {TODAY}: {brand}"}]) in (200,201)

def update_reason(email, reason):
    supa("PATCH", f"{SUPA}?channel=eq.email&recipient=eq.{urllib.parse.quote(email)}", {"reason":reason})

def body_for(first_name, brand):
    greeting = f"Hi {first_name}," if first_name else "Hi there,"
    return f"""{greeting}

We're Stanford/Dartmouth students building AI tools for DTC brands. We're already working with $100M brands like Public Goods and Good Molecules, and we've been talking with the teams behind brands like {brand} to understand what's actually hard about growing online.

Would you be open to a quick 10-minute call?

If not, even a one-sentence reply on your biggest challenge right now would be a huge help.

Thanks,
{SENDER_NAME}"""

def html_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def body_html_for(first_name, brand):
    """Rich-text (HTML) version of the opener. Kept deliberately minimal: real
    paragraphs, system font, no images or heavy styling (which hurt cold-email
    deliverability and feel less personal). A plaintext alternative is always
    sent alongside as the fallback."""
    greeting = f"Hi {html_escape(first_name)}," if first_name else "Hi there,"
    b = html_escape(brand)
    return f"""<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:#222;">
<p>{greeting}</p>
<p>We're Stanford/Dartmouth students building AI tools for DTC brands. We're already working with $100M brands like Public Goods and Good Molecules, and we've been talking with the teams behind brands like {b} to understand what's actually hard about growing online.</p>
<p>Would you be open to a quick 10-minute call?</p>
<p>If not, even a one-sentence reply on your biggest challenge right now would be a huge help.</p>
<p>Thanks,<br>{html_escape(SENDER_NAME)}</p>
</div>"""

def send(to, first_name, brand):
    subject = SUBJECT_TMPL.format(brand=brand)
    p = subprocess.run(["gog","gmail","send","-a",ACC,"--to",to,"--cc",CC,
                        "--subject",subject,"--body",body_for(first_name,brand),
                        "--body-html",body_html_for(first_name,brand),"--no-input"],
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
        update_reason(email, f"contacted {TODAY}: blackwell volume cold email ({brand}; msg {detail})")
        counts["sent"] += 1
        if counts["sent"] % 10 == 0: print(f"... {counts['sent']} sent", flush=True)
    else:
        update_reason(email, f"send FAILED {TODAY} ({brand}): {detail[:100]}")
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
