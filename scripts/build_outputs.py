#!/usr/bin/env python3
import os, json, re, uuid
from datetime import datetime, timedelta, timezone

# --- Config (works whether your events live at repo root or in /data) ---
HTML_PATH = "index.html"
ICS_PATH  = "London_Expos.ics"
EVENTS_JSON = None
for candidate in ("events.json", "data/events.json"):
    if os.path.exists(candidate):
        EVENTS_JSON = candidate
        break
if not EVENTS_JSON:
    raise FileNotFoundError("Could not find events.json. Put it at repo root or in /data/events.json.")

# --- Helpers ---
def load_events():
    with open(EVENTS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_iso(dt_str: str) -> datetime:
    # Keep any timezone in the string; if none, assume UTC to be safe
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def within_next_three_months(dt: datetime) -> bool:
    now = datetime.now(timezone.utc)
    return now <= dt <= (now + timedelta(days=92))

def esc(s: str) -> str:
    s = (s or "")
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def to_utc_ics(dt: datetime) -> str:
    # RFC5545: YYYYMMDDTHHMMSSZ
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def write_ics(events):
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ExpoApp//London Expos//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:London Expos (Next 3 Months)"
    ]
    for e in events:
        start = to_utc_ics(parse_iso(e["start"]))  # <-- UTC with trailing Z
        end   = to_utc_ics(parse_iso(e["end"]))    # <-- UTC with trailing Z
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}@expoapp",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{start}",
            f"DTEND:{end}",
            f"SUMMARY:{esc(e['title'])}",
            f"LOCATION:{esc(e.get('venue',''))}",
            f"DESCRIPTION:{esc((e['title'] + ' — ' + (e.get('url') or '')).strip())}",
            f"URL:{e.get('url','')}",
            "END:VEVENT"
        ]
    lines.append("END:VCALENDAR")
    with open(ICS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def inject_events_into_html(html_text: str, events_window):
    # Replace the `const allEvents = [ ... ];` blob with the windowed list
    m = re.search(r'const allEvents = (\[.*?\]);', html_text, flags=re.DOTALL)
    if not m:
        return html_text  # no injection point found; leave HTML as-is
    new_blob = json.dumps(events_window, ensure_ascii=False)
    return re.sub(r'const allEvents = \[.*?\];',
                  f'const allEvents = {new_blob};',
                  html_text, flags=re.DOTALL)

def main():
    # 1) Load master events (you maintain this file)
    all_events = load_events()

    # 2) Filter to the NEXT 3 months
    events_window = []
    for e in all_events:
        try:
            start_dt = parse_iso(e["start"])
        except Exception:
            continue
        if within_next_three_months(start_dt):
            events_window.append(e)

    # 3) Rebuild ICS (with UTC Z timestamps)
    write_ics(events_window)

    # 4) Update index.html's allEvents array with the same 3-month window
    if os.path.exists(HTML_PATH):
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
        html = inject_events_into_html(html, events_window)
        with open(HTML_PATH, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"Built {len(events_window)} events for next 3 months")

if __name__ == "__main__":
    main()
