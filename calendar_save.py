import sqlite3
import csv
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from ics import Calendar, Event
from ics.alarm import DisplayAlarm
from ics.grammar.parse import ContentLine
import pytz

# Optional: python calendar_save.py [Calendar.sqlitedb] [output_dir]
DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "Calendar.sqlitedb"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "."

OUTPUT_ICS = os.path.join(OUT_DIR, "apple_calendar_full_export.ics")
OUTPUT_CSV = os.path.join(OUT_DIR, "apple_calendar_export.csv")
CALENDAR_DIR = os.path.join(OUT_DIR, "calendars")

APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)

def apple_time(seconds):
    if seconds is None:
        return None
    return APPLE_EPOCH + timedelta(seconds=seconds)

def apple_date(seconds):
    return apple_time(seconds).date()

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cal = Calendar()
csv_data = []  # Store event data for CSV export
sub_calendars = {}  # calendar_id -> {"title": str, "cal": Calendar}


def calendar_filename(title, calendar_id, used):
    """Turn a calendar title into a unique, filesystem-safe .ics filename."""
    slug = re.sub(r"[^\w\-]+", "_", (title or "").strip(), flags=re.UNICODE).strip("_")
    slug = slug or f"calendar_{calendar_id}"
    # Two calendars can share a title (e.g. duplicate subscriptions) - keep both
    if slug.lower() in used:
        slug = f"{slug}_{calendar_id}"
    used.add(slug.lower())
    return slug + ".ics"

# =========================
# MAIN EVENT QUERY
# =========================
events = cur.execute("""
SELECT
    ci.ROWID            AS event_id,
    ci.UUID             AS uid,
    ci.summary          AS title,
    ci.description      AS notes,
    ci.location_id      AS location_id,
    ci.start_date       AS start_date,
    ci.end_date         AS end_date,
    ci.all_day          AS all_day,
    ci.start_tz         AS timezone,
    ci.organizer_id     AS organizer_id,
    ci.has_recurrences  AS has_recurrence,
    ci.entity_type      AS entity_type,
    ci.calendar_id      AS calendar_id,
    c.title             AS calendar_title
FROM CalendarItem ci
LEFT JOIN Calendar c ON c.ROWID = ci.calendar_id
WHERE ci.start_date IS NOT NULL
ORDER BY ci.start_date DESC
""").fetchall()

print(f"Found {len(events)} calendar items in database")

for row in events:
    e = Event()

    # ---- Core fields ----
    e.uid = row["uid"]
    e.name = row["title"] or "Untitled Event"
    e.description = row["notes"]

    # Location lookup if location_id exists
    location_text = ""
    if row["location_id"]:
        loc_result = cur.execute("SELECT title FROM Location WHERE ROWID = ?", (row["location_id"],)).fetchone()
        if loc_result:
            location_text = loc_result[0]
    e.location = location_text

    # Handle timezone safely
    tz = pytz.UTC
    if row["timezone"]:
        try:
            tz = pytz.timezone(row["timezone"])
        except pytz.exceptions.UnknownTimeZoneError:
            # If timezone is invalid, try to use system timezone or default to UTC
            tz = pytz.UTC

    if row["all_day"]:
        e.begin = apple_date(row["start_date"])
        e.make_all_day()
    else:
        e.begin = apple_time(row["start_date"]).astimezone(tz)
        if row["end_date"]:
            e.end = apple_time(row["end_date"]).astimezone(tz)

    # ---- Organizer ----
    organizer_email = ""
    if row["organizer_id"]:
        org_result = cur.execute("SELECT address FROM Identity WHERE ROWID = ?", (row["organizer_id"],)).fetchone()
        if org_result and org_result[0]:
            organizer_email = org_result[0]
            # Remove MAILTO: prefix if present
            if organizer_email.upper().startswith("MAILTO:"):
                organizer_email = organizer_email[7:]
            e.organizer = organizer_email

    # =========================
    # RECURRENCE RULES (RRULE)
    # =========================
    if row["has_recurrence"]:
        rrule = cur.execute("""
        SELECT
            frequency,
            interval,
            count,
            end_date,
            specifier,
            by_month_months
        FROM Recurrence
        WHERE owner_id = ?
        """, (row["event_id"],)).fetchone()

        if rrule:
            rule = {}

            freq_map = {
                0: "DAILY",
                1: "WEEKLY",
                2: "MONTHLY",
                3: "YEARLY"
            }

            rule["FREQ"] = freq_map.get(rrule["frequency"], "DAILY")

            if rrule["interval"] and rrule["interval"] > 1:
                rule["INTERVAL"] = rrule["interval"]

            if rrule["count"] and rrule["count"] > 0:
                rule["COUNT"] = rrule["count"]

            if rrule["end_date"]:
                rule["UNTIL"] = apple_time(rrule["end_date"])

            # Parse the specifier field if it contains additional rule info
            if rrule["specifier"]:
                # The specifier might contain BYDAY, BYMONTHDAY, etc.
                # Parse it and add to rule (it's often in iCalendar format)
                spec = rrule["specifier"].strip()
                if spec:
                    # Try to parse common patterns
                    for part in spec.split(';'):
                        if '=' in part:
                            key, value = part.split('=', 1)
                            rule[key.strip()] = value.strip()

            # Note: RRULE handling via e.extra causes serialization issues
            # The ics library doesn't support complex RRULE via extra field
            # Would need to use a different approach or library for full RRULE support

        # ---- Recurrence exceptions (EXDATE) ----
        exdates = cur.execute("""
        SELECT date
        FROM ExceptionDate
        WHERE owner_id = ?
        """, (row["event_id"],)).fetchall()

        # Note: EXDATE handling also has serialization issues with the ics library

    # =========================
    # ALARMS / REMINDERS
    # =========================
    alarms = []
    try:
        alarms = cur.execute("""
        SELECT trigger
        FROM Alarm
        WHERE owner_id = ?
        """, (row["event_id"],)).fetchall()
    except sqlite3.OperationalError:
        # Table or column doesn't exist, try Notification table
        try:
            alarms = cur.execute("""
            SELECT trigger_interval
            FROM Notification
            WHERE owner_id = ?
            """, (row["event_id"],)).fetchall()
        except sqlite3.OperationalError:
            # No alarms available
            pass

    for alarm in alarms:
        a = DisplayAlarm()
        # Handle both 'trigger' and 'trigger_interval' field names
        trigger_value = alarm.get("trigger") or alarm.get("trigger_interval") or alarm[0]
        a.trigger = timedelta(seconds=-trigger_value)
        e.alarms.append(a)

    # =========================
    # ATTENDEES / CONTACTS
    # =========================
    attendees = []
    try:
        attendees = cur.execute("""
        SELECT email, name, status
        FROM Attendee
        WHERE owner_id = ?
        """, (row["event_id"],)).fetchall()
    except sqlite3.OperationalError:
        # Try Participant table instead
        try:
            attendees = cur.execute("""
            SELECT email, display_name as name, status
            FROM Participant
            WHERE owner_id = ?
            """, (row["event_id"],)).fetchall()
        except sqlite3.OperationalError:
            # No attendees available
            pass

    # Note: ATTENDEE handling via e.extra also causes serialization issues
    # The ics library has limited support for attendees via extra field

    # =========================
    # COLLECT DATA FOR CSV
    # =========================
    csv_row = {
        "UID": row["uid"],
        "Calendar": row["calendar_title"] or "Unassigned",
        "Title": row["title"] or "Untitled Event",
        "Start Date": str(apple_time(row["start_date"]) if not row["all_day"] else apple_date(row["start_date"])),
        "End Date": str(apple_time(row["end_date"]) if row["end_date"] and not row["all_day"] else (apple_date(row["end_date"]) if row["end_date"] else "")),
        "All Day": "Yes" if row["all_day"] else "No",
        "Location": location_text,
        "Description": (row["notes"] or "").replace("\n", " ").replace("\r", " ")[:200],  # Truncate long descriptions
        "Timezone": row["timezone"] or "",
        "Organizer": organizer_email,
        "Has Recurrence": "Yes" if row["has_recurrence"] else "No",
        "Alarm Count": len(alarms),
        "Attendee Count": len(attendees),
    }
    csv_data.append(csv_row)

    cal.events.add(e)

    # ---- Also file the event under the calendar it came from ----
    cal_id = row["calendar_id"]
    if cal_id not in sub_calendars:
        sub_calendars[cal_id] = {
            "title": row["calendar_title"] or "Unassigned",
            "cal": Calendar(),
        }
    sub_calendars[cal_id]["cal"].events.add(e)

conn.close()

# =========================
# WRITE ICS FILE
# =========================
with open(OUTPUT_ICS, "w", encoding="utf-8") as f:
    f.writelines(cal)

print(f"✅ Exported {len(cal.events)} events to {OUTPUT_ICS}")

# =========================
# WRITE ONE ICS PER CALENDAR
# =========================
os.makedirs(CALENDAR_DIR, exist_ok=True)
used_names = set()

# Biggest calendars first, so the listing reads like the import order
for cal_id, entry in sorted(sub_calendars.items(), key=lambda kv: -len(kv[1]["cal"].events)):
    sub_cal = entry["cal"]
    # X-WR-CALNAME makes the calendar import under its real name instead of the
    # file name. ContentLine (not a raw tuple) is what ics 0.7 can serialize.
    sub_cal.extra.append(ContentLine(name="X-WR-CALNAME", value=entry["title"]))

    filename = calendar_filename(entry["title"], cal_id, used_names)
    path = os.path.join(CALENDAR_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(sub_cal)

    print(f"   {len(sub_cal.events):5d}  {filename}")

print(f"✅ Exported {len(sub_calendars)} calendars to {CALENDAR_DIR}/")

# =========================
# WRITE CSV FILE
# =========================
if csv_data:
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["UID", "Calendar", "Title", "Start Date", "End Date", "All Day", "Location",
                      "Description", "Timezone", "Organizer", "Has Recurrence",
                      "Alarm Count", "Attendee Count"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)

    print(f"✅ Exported {len(csv_data)} events to {OUTPUT_CSV}")
else:
    print("⚠️  No events to export to CSV")

