#!/usr/bin/env python3
"""Team email-send counter, derived from the ledger (the single source of truth).

Every outreach path in this repo records each send in Supabase before sending:
the volume senders (send_fast.py / send_taste_data.py) and the interactive Clay
sends write the `suppression` table with a reason that starts with "contacted ";
the harness `gmail.send` primitive writes the `contacted` table. So the real
team send count is just: rows in `contacted` + suppression rows whose reason
starts with "contacted ", bucketed by date. Nothing to increment, nothing that
can drift.

Excluded from the counts: pre-company Giftly-era imports (reason contains
"giftly"), bounces, failed sends ("send FAILED"), and claimed-but-not-confirmed
rows ("CLAIMED ..."). The Giftly historical "sent" total is reported separately.

Run: `python skills/outreach-counter/counter.py`  (prints the counts and
rewrites agents/outreach/send-counts.md). Reads Supabase creds from the
environment, falling back to credentials/.env.
"""
import datetime, json, os, re, sys, urllib.request, urllib.error
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "agents" / "outreach" / "send-counts.md"
TZ = ZoneInfo("America/Los_Angeles")  # bucket "day"/"week" in Pacific time


def load_env():
    for k in ("SUPABASE_URL", "SUPABASE_SECRET_KEY"):
        if os.environ.get(k):
            continue
        env = ROOT / "credentials" / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                m = re.match(r"\s*([A-Z_]+)\s*=\s*(.*)\s*$", line)
                if m and not os.environ.get(m.group(1)):
                    os.environ[m.group(1)] = m.group(2).strip()
        break


def fetch(table, cols):
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SECRET_KEY"]
    out, step, start = [], 1000, 0
    while True:
        req = urllib.request.Request(
            f"{base}/rest/v1/{table}?select={cols}",
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Range-Unit": "items", "Range": f"{start}-{start+step-1}"})
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            sys.stderr.write(f"WARN {table}: HTTP {e.code}\n")
            break
        if not data:
            break
        out += data
        if len(data) < step:
            break
        start += step
    return out


def local_date(iso):
    if not iso:
        return None
    s = iso.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(s).astimezone(TZ).date()
    except ValueError:
        return None


def campaign_tag(reason):
    """Short label from a 'contacted ...' reason, for the per-campaign table."""
    r = (reason or "").strip()
    r = re.sub(r"^contacted\s+", "", r, flags=re.I)
    r = re.sub(r"\s*\(.*", "", r)          # drop the per-recipient parenthetical
    r = re.sub(r"\d{4}-\d{2}-\d{2}:?", "", r).strip(" :-")  # drop dates
    return r or "blackwell"


def main():
    load_env()
    supp = fetch("suppression", "reason,created_at")
    cont = fetch("contacted", "created_at")

    sends = []   # (date, campaign_tag)
    for r in supp:
        reason = (r.get("reason") or "").strip()
        if reason.lower().startswith("contacted "):
            d = local_date(r.get("created_at"))
            if d:
                sends.append((d, campaign_tag(reason)))
    for r in cont:
        d = local_date(r.get("created_at"))
        if d:
            sends.append((d, "harness gmail.send"))

    giftly = sum(1 for r in supp
                 if "giftly" in (r.get("reason") or "").lower()
                 and ":sent" in (r.get("reason") or "").lower())

    today = datetime.datetime.now(TZ).date()
    week_start = today - datetime.timedelta(days=6)  # rolling 7 days incl. today
    by_day = Counter(d for d, _ in sends)
    day_n = by_day.get(today, 0)
    week_n = sum(v for d, v in by_day.items() if week_start <= d <= today)
    total_n = len(sends)

    # report
    print(f"TODAY ({today}): {day_n}")
    print(f"THIS WEEK ({week_start}..{today}): {week_n}")
    print(f"TOTAL (this system): {total_n}")

    last14 = sorted(by_day)[-14:]
    by_camp = Counter(t for _, t in sends)
    stamp = datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M %Z")

    lines = []
    lines.append("# Team email send counts")
    lines.append("")
    lines.append(f"Auto-generated from the Supabase ledger by "
                 f"`skills/outreach-counter/counter.py`. Last updated {stamp}.")
    lines.append("Counts every team send (volume senders, Clay, and the harness "
                 "`gmail.send`), since each records to the ledger before sending. "
                 "Day and week are bucketed in US Pacific time.")
    lines.append("")
    lines.append("| Counter | Emails sent |")
    lines.append("|---|---|")
    lines.append(f"| Today ({today}) | {day_n} |")
    lines.append(f"| This week (rolling 7 days, {week_start} to {today}) | {week_n} |")
    lines.append(f"| Total (all-time, this system) | {total_n} |")
    lines.append("")
    lines.append("## Sends per day (last 14 active days)")
    lines.append("")
    lines.append("| Date | Sent |")
    lines.append("|---|---|")
    for d in last14:
        lines.append(f"| {d} | {by_day[d]} |")
    lines.append("")
    lines.append("## By campaign")
    lines.append("")
    lines.append("| Campaign | Sent |")
    lines.append("|---|---|")
    for tag, n in by_camp.most_common():
        lines.append(f"| {tag} | {n} |")
    lines.append("")
    lines.append(f"Excluded from the counts above: {giftly} pre-company Giftly-era "
                 "imports, plus bounces and failed/unconfirmed sends. Include the "
                 f"Giftly history and the all-time figure becomes {total_n + giftly}.")
    lines.append("")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
