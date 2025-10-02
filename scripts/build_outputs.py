#!/usr/bin/env python3
import json, re, uuid
from datetime import datetime, timedelta

EVENTS_JSON = "events.json"       # we keep it at the repo root
HTML_IN_OUT = "index.html"        # update in place
ICS_OUT = "London_Expos.ics"

def load_events():
    with open(EVENTS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def within_next_three_months(dt):
    now = datetime.now()
    return now <= dt <= (now + timedelta(days=92))

def write_ics(events):
    def esc(s): return s.replace("\\","\\\\").replace(";","\\;").replace(",","\\,").replace("\n","\\n")
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//ExpoApp//London Expos//EN","CALSCALE:GREGORIAN","METHOD:PUBLISH"]
    for e in events:
        uid = str(uuid.uuid4()) + "@expoapp"
        lines += ["BEGIN:VEVENT",
                  f"UID:{uid}",
                  f"DTSTAMP:{dtstamp}",
                  f"DTSTART:{e['start'].replace('-','').replace(':','')}",
                  f"DTEND:{e['end'].replace('-','').replace(':','')}",
                  f"SUMMARY:{esc(e['title'])}",
                  f"LOCATION:{esc(e.get('venue',''))}",
                  f"DESCRIPTION:{esc(e['title']+' — '+e.get('url',''))}",
                  f"URL:{e.get('url','')}",
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    with open(ICS_OUT,"w",encoding="utf-8") as f: f.write("\n".join(lines))

def inject_events_into_html(html, events):
    m = re.search(r'const allEvents = (\[.*?\]);', html, flags=re.DOTALL)
    if not m: return html
    new_blob = json.dumps(events, ensure_ascii=False)
    return re.sub(r'const allEvents = \[.*?\];', f'const allEvents = {new_blob};', html, flags=re.DOTALL)

def main():
    all_events = load_events()  # you maintain this list (can include future items)
    def parse_iso(s): return datetime.fromisoformat(s.replace("Z","+00:00").split("+")[0])
    window = [e for e in all_events if within_next_three_months(parse_iso(e["start"]))]
    write_ics(window)
    with open(HTML_IN_OUT,"r",encoding="utf-8") as f: html=f.read()
    new_html = inject_events_into_html(html, window)
    with open(HTML_IN_OUT,"w",encoding="utf-8") as f: f.write(new_html)
    print(f"Built {len(window)} events for next 3 months")

if __name__ == "__main__":
    main()
