#!/usr/bin/env python3
"""
iPhone Calendar Rescue
======================

Turns an iPhone/iPad backup into .ics calendar files you can import into
Apple Calendar, Google Calendar, Outlook, Thunderbird - anything really.

You only need to give it one path:

    python3 calendar_rescue.py "/path/to/backup-folder"
    python3 calendar_rescue.py "/path/to/Calendar.sqlitedb"
    python3 calendar_rescue.py                 # finds your backups by itself

This script needs nothing but Python itself - no pip install, no internet.

Licensed MIT. Written with AI assistance; see the README.
"""

from __future__ import annotations

import argparse
import csv
import os
import plistlib
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

__version__ = "1.0.0"

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

# Apple stores every timestamp as "seconds since 1 January 2001, UTC".
APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)

# Where the calendar database lives inside an iPhone backup.
CAL_DOMAIN = "HomeDomain"
CAL_RELPATH = "Library/Calendar/Calendar.sqlitedb"

SQLITE_MAGIC = b"SQLite format 3\x00"

# How Apple numbers repeat rules in this database. (1-based, not 0-based.)
FREQUENCY = {1: "DAILY", 2: "WEEKLY", 3: "MONTHLY", 4: "YEARLY"}

# Participant.status -> iCalendar PARTSTAT
PARTSTAT = {0: "NEEDS-ACTION", 1: "ACCEPTED", 2: "DECLINED", 3: "TENTATIVE",
            4: "DELEGATED", 5: "ACCEPTED", 6: "COMPLETED", 7: "IN-PROCESS"}


# --------------------------------------------------------------------------
# Talking to the user
# --------------------------------------------------------------------------

QUIET = False


def say(message=""):
    if not QUIET:
        print(message)


def step(number, message):
    say(f"\n[{number}] {message}")


def warn(message):
    print(f"  ! {message}")


def die(message, *hints):
    """Print a friendly explanation and stop. Never show a Python traceback."""
    sys.stdout.flush()  # keep the message in order when output is redirected
    print(f"\nSTOPPED: {message}\n", file=sys.stderr)
    for hint in hints:
        print(f"  -> {hint}", file=sys.stderr)
    if hints:
        print(file=sys.stderr)
    sys.exit(1)


def permission_help(path):
    """macOS hides the backup folder from programs until you allow it."""
    if sys.platform == "darwin":
        die(
            f"macOS will not let this script read:\n    {path}",
            "This is a macOS privacy setting, not a problem with your backup.",
            "Open: System Settings -> Privacy & Security -> Full Disk Access",
            "Switch ON the app you are running this from (usually 'Terminal').",
            "Quit Terminal completely, reopen it, and run the command again.",
        )
    die(
        f"No permission to read:\n    {path}",
        "Try running the command again from an administrator window.",
    )


# --------------------------------------------------------------------------
# Finding a backup on this computer
# --------------------------------------------------------------------------

def default_backup_roots():
    """The folders where iTunes / Finder keep backups, per platform."""
    home = os.path.expanduser("~")
    candidates = []
    if sys.platform == "darwin":
        candidates.append(os.path.join(
            home, "Library", "Application Support", "MobileSync", "Backup"))
    elif os.name == "nt":
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        candidates.append(os.path.join(appdata, "Apple Computer", "MobileSync", "Backup"))
        candidates.append(os.path.join(appdata, "Apple", "MobileSync", "Backup"))
        candidates.append(os.path.join(home, "Apple", "MobileSync", "Backup"))
    return [p for p in candidates if os.path.isdir(p)]


def is_backup_folder(path):
    return os.path.isfile(os.path.join(path, "Manifest.db")) or \
           os.path.isfile(os.path.join(path, "Manifest.plist"))


def backup_label(path):
    """A human description of one backup: device name and date."""
    name, when = None, None
    try:
        with open(os.path.join(path, "Info.plist"), "rb") as handle:
            info = plistlib.load(handle)
        name = info.get("Device Name") or info.get("Product Name")
        when = info.get("Last Backup Date")
    except Exception:
        pass
    if when is None:
        try:
            when = datetime.fromtimestamp(os.path.getmtime(path))
        except OSError:
            when = None
    parts = [name or os.path.basename(path)]
    if when:
        parts.append(when.strftime("%d %B %Y"))
    return " - ".join(parts)


def find_backups():
    """Every backup we can see, newest first."""
    found = []
    for root in default_backup_roots():
        try:
            entries = sorted(os.listdir(root))
        except PermissionError:
            permission_help(root)
        except OSError:
            continue
        for entry in entries:
            full = os.path.join(root, entry)
            if os.path.isdir(full) and is_backup_folder(full):
                found.append(full)
    found.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return found


# --------------------------------------------------------------------------
# Getting Calendar.sqlitedb out of a backup
# --------------------------------------------------------------------------

def backup_is_encrypted(backup_dir):
    manifest = os.path.join(backup_dir, "Manifest.plist")
    if not os.path.isfile(manifest):
        return False
    try:
        with open(manifest, "rb") as handle:
            return bool(plistlib.load(handle).get("IsEncrypted", False))
    except PermissionError:
        permission_help(manifest)
    except Exception:
        return False


def extract_from_backup(backup_dir, destination):
    """Copy the calendar database (and its sidecar files) out of a backup."""
    if backup_is_encrypted(backup_dir):
        die(
            "This backup is encrypted, so the calendar cannot be read from it.",
            "In Finder (Mac) or iTunes/Apple Devices (Windows), untick",
            "  'Encrypt local backup', then make a fresh backup and use that one.",
            "Or export just Calendar.sqlitedb with iTunes Backup Explorer -",
            "  the README explains how, and it can open encrypted backups.",
        )

    manifest_db = os.path.join(backup_dir, "Manifest.db")
    if not os.path.isfile(manifest_db):
        if os.path.isfile(os.path.join(backup_dir, "Manifest.mbdb")):
            die(
                "This backup was made by a very old iOS version (iOS 9 or older)"
                " and uses a format this script cannot read.",
                "Make a new backup with a current iPhone, or use"
                " iTunes Backup Explorer to export the calendar file by hand.",
            )
        die(
            f"This folder does not look like an iPhone backup:\n    {backup_dir}",
            "An iPhone backup folder contains a file called 'Manifest.db'.",
            "Point the script at the folder named like a long string of letters"
            " and numbers, not at the folder above it.",
        )

    try:
        connection = sqlite3.connect(f"file:{manifest_db}?mode=ro", uri=True)
        rows = connection.execute(
            "SELECT fileID, relativePath FROM Files "
            "WHERE domain = ? AND relativePath LIKE ?",
            (CAL_DOMAIN, CAL_RELPATH + "%"),
        ).fetchall()
        connection.close()
    except PermissionError:
        permission_help(manifest_db)
    except sqlite3.DatabaseError:
        die(
            "The backup's index file (Manifest.db) could not be read.",
            "If the backup is encrypted, see the README - encrypted backups"
            " scramble this file too.",
        )

    if not rows:
        die(
            "This backup does not contain a calendar database.",
            "That usually means the backup is encrypted, or the phone had"
            " iCloud Calendar switched on, so events were never stored locally.",
            "The README explains what to try next.",
        )

    os.makedirs(destination, exist_ok=True)
    main_db = None
    for file_id, relative_path in rows:
        source = os.path.join(backup_dir, file_id[:2], file_id)
        if not os.path.isfile(source):
            continue
        target = os.path.join(destination, os.path.basename(relative_path))
        try:
            shutil.copyfile(source, target)
        except PermissionError:
            permission_help(source)
        say(f"  found {os.path.basename(relative_path)}"
            f"  ({os.path.getsize(target) / 1_000_000:.1f} MB)")
        if relative_path.endswith("Calendar.sqlitedb"):
            main_db = target

    if not main_db:
        die("The calendar database is listed in the backup but its data file is"
            " missing. The backup is probably incomplete.",
            "Make a fresh backup and try again.")
    return main_db


def looks_like_sqlite(path):
    try:
        with open(path, "rb") as handle:
            return handle.read(16) == SQLITE_MAGIC
    except PermissionError:
        permission_help(path)
    except OSError:
        return False


def resolve_input(given, workdir):
    """Work out what the user handed us and return a calendar database path."""
    if given is None:
        backups = find_backups()
        if not backups:
            die(
                "No iPhone backup found in the usual place on this computer.",
                "Backups are usually in one of these folders - but not always,"
                " they are often moved to an external drive:",
                "   Mac:     ~/Library/Application Support/MobileSync/Backup/",
                "   Windows: C:\\Users\\<you>\\Apple\\MobileSync\\Backup",
                "   Windows: C:\\Users\\<you>\\AppData\\Roaming\\Apple"
                " Computer\\MobileSync\\Backup",
                "If yours is somewhere else, pass that folder to this script.",
                "No backup yet? Make one - but copy any older backup somewhere"
                " safe first, because a new backup can overwrite it.",
            )
        chosen = backups[0]
        say(f"  using your most recent backup: {backup_label(chosen)}")
        if len(backups) > 1:
            say(f"  {len(backups) - 1} older backup(s) are also here. If events"
                f" are missing, try an older one - pass its folder path:")
            for older in backups[1:4]:
                say(f"     {older}")
        return extract_from_backup(chosen, workdir)

    given = os.path.expanduser(given)
    if not os.path.exists(given):
        die(f"Nothing found at:\n    {given}",
            "Check the path. On Mac you can drag the file or folder into the"
            " Terminal window to paste its path correctly.")

    if os.path.isfile(given):
        if not looks_like_sqlite(given):
            die(f"This file is not a calendar database:\n    {given}",
                "You are looking for a file called 'Calendar.sqlitedb'.")
        return given

    # A folder. Three possibilities.
    if is_backup_folder(given):
        say(f"  reading backup: {backup_label(given)}")
        return extract_from_backup(given, workdir)

    # The folder that holds several backups?
    children = []
    try:
        children = [os.path.join(given, e) for e in sorted(os.listdir(given))]
    except PermissionError:
        permission_help(given)
    backups = [c for c in children if os.path.isdir(c) and is_backup_folder(c)]
    if backups:
        backups.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        say(f"  found {len(backups)} backup(s) here, using the newest:"
            f" {backup_label(backups[0])}")
        return extract_from_backup(backups[0], workdir)

    # A folder someone exported the calendar file into?
    for child in children:
        if os.path.isfile(child) and os.path.basename(child) == "Calendar.sqlitedb":
            return child
    for child in children:
        if os.path.isfile(child) and looks_like_sqlite(child):
            return child

    die(f"No backup and no calendar database found in:\n    {given}",
        "Point the script at your backup folder, or at the Calendar.sqlitedb"
        " file itself.")


# --------------------------------------------------------------------------
# Reading the calendar
# --------------------------------------------------------------------------

def apple_time(seconds):
    if seconds is None:
        return None
    return APPLE_EPOCH + timedelta(seconds=seconds)


def read_calendar(db_path):
    """Return (list of calendars, each with its events)."""
    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.DatabaseError:
        die(f"This file is damaged or not a calendar database:\n    {db_path}")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM CalendarItem")
    except sqlite3.DatabaseError:
        die(f"This is a database, but not an iPhone calendar:\n    {db_path}",
            "You are looking for the file called 'Calendar.sqlitedb'.")

    items = cursor.execute("""
        SELECT ci.ROWID AS id, ci.UUID AS uid, ci.summary, ci.description,
               ci.start_date, ci.end_date, ci.all_day, ci.location_id,
               ci.organizer_id, ci.has_recurrences, ci.url,
               ci.calendar_id, cal.title AS calendar_title, cal.color
        FROM CalendarItem ci
        LEFT JOIN Calendar cal ON cal.ROWID = ci.calendar_id
        WHERE ci.start_date IS NOT NULL
        ORDER BY ci.start_date
    """).fetchall()

    calendars = {}
    quirks = {"ancient": 0, "no_end": 0}

    for item in items:
        event = {
            "uid": item["uid"] or f"calendar-rescue-{item['id']}",
            "summary": item["summary"] or "(no title)",
            "description": item["description"],
            "url": item["url"],
            "all_day": bool(item["all_day"]),
            "start": apple_time(item["start_date"]),
            "end": apple_time(item["end_date"]),
            "location": None,
            "organizer": None,
            "rrule": None,
            "exdates": [],
            "alarms": [],
            "attendees": [],
        }
        if event["end"] is None:
            quirks["no_end"] += 1
        if event["start"].year < 1900:
            quirks["ancient"] += 1

        if item["location_id"]:
            row = cursor.execute(
                "SELECT title FROM Location WHERE ROWID = ?",
                (item["location_id"],)).fetchone()
            if row and row["title"]:
                event["location"] = row["title"]

        if item["organizer_id"]:
            row = cursor.execute(
                "SELECT address FROM Identity WHERE ROWID = ?",
                (item["organizer_id"],)).fetchone()
            if row and row["address"]:
                event["organizer"] = strip_mailto(row["address"])

        if item["has_recurrences"]:
            event["rrule"] = read_rrule(cursor, item["id"])
            event["exdates"] = [
                apple_time(r["date"]) for r in cursor.execute(
                    "SELECT date FROM ExceptionDate WHERE owner_id = ?",
                    (item["id"],)).fetchall() if r["date"] is not None]

        event["alarms"] = read_alarms(cursor, item["id"])
        event["attendees"] = read_attendees(cursor, item["id"])

        key = item["calendar_id"]
        if key not in calendars:
            calendars[key] = {
                "id": key,
                "name": item["calendar_title"] or "Unsorted",
                "color": item["color"],
                "events": [],
            }
        calendars[key]["events"].append(event)

    connection.close()
    ordered = sorted(calendars.values(), key=lambda c: -len(c["events"]))
    return ordered, quirks


def strip_mailto(address):
    return address[7:] if address.upper().startswith("MAILTO:") else address


def read_rrule(cursor, event_id):
    """Build an iCalendar repeat rule from Apple's Recurrence row."""
    row = cursor.execute("""
        SELECT frequency, interval, count, end_date, specifier
        FROM Recurrence WHERE owner_id = ?
    """, (event_id,)).fetchone()
    if not row:
        return None

    parts = ["FREQ=" + FREQUENCY.get(row["frequency"], "DAILY")]
    if row["interval"] and row["interval"] > 1:
        parts.append(f"INTERVAL={row['interval']}")
    if row["count"] and row["count"] > 0:
        parts.append(f"COUNT={row['count']}")
    elif row["end_date"]:
        until = apple_time(row["end_date"])
        parts.append("UNTIL=" + until.strftime("%Y%m%dT%H%M%SZ"))

    # Apple writes extras like "D=+1SU;O=10" (first Sunday, in October).
    for chunk in (row["specifier"] or "").split(";"):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        key, value = key.strip().upper(), value.strip()
        if not value:
            continue
        if key == "D":
            days = [d[1:] if d.startswith("0") else d for d in value.split(",")]
            parts.append("BYDAY=" + ",".join(days))
        elif key == "O":
            parts.append("BYMONTH=" + value)
    return ";".join(parts)


def read_alarms(cursor, event_id):
    """Reminder offsets, in seconds before the event."""
    try:
        rows = cursor.execute("""
            SELECT trigger_interval FROM Alarm
            WHERE calendaritem_owner_id = ? AND trigger_interval IS NOT NULL
        """, (event_id,)).fetchall()
    except sqlite3.DatabaseError:
        return []
    return [int(r["trigger_interval"]) for r in rows]


def read_attendees(cursor, event_id):
    try:
        rows = cursor.execute("""
            SELECT p.email, p.status, i.display_name
            FROM Participant p
            LEFT JOIN Identity i ON i.ROWID = p.identity_id
            WHERE p.owner_id = ?
        """, (event_id,)).fetchall()
    except sqlite3.DatabaseError:
        return []
    people = []
    for row in rows:
        address = row["email"] or (row["display_name"] or "")
        if not address:
            continue
        people.append({
            "email": strip_mailto(address),
            "name": row["display_name"],
            "partstat": PARTSTAT.get(row["status"], "NEEDS-ACTION"),
        })
    return people


# --------------------------------------------------------------------------
# Writing .ics files (plain text, built by hand - no libraries needed)
# --------------------------------------------------------------------------

def escape(text):
    """iCalendar reserves a few characters."""
    return (str(text).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\r\n", "\\n")
            .replace("\n", "\\n").replace("\r", "\\n"))


def fold(line):
    """iCalendar lines must not exceed 75 bytes; longer ones continue
    on the next line, indented by one space."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    pieces, start = [], 0
    limit = 75
    while start < len(raw):
        end = min(start + limit, len(raw))
        # Don't split in the middle of a multi-byte character.
        while end > start and end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        pieces.append(raw[start:end].decode("utf-8"))
        start = end
        limit = 74  # continuation lines lose one byte to the leading space
    return "\r\n ".join(pieces)


def stamp(moment, all_day):
    if all_day:
        return ";VALUE=DATE:" + moment.strftime("%Y%m%d")
    return ":" + moment.strftime("%Y%m%dT%H%M%SZ")


def duration(seconds):
    """Seconds (negative = before the event) as an iCalendar duration."""
    sign = "-" if seconds < 0 else ""
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    out = sign + "P"
    if days:
        out += f"{days}D"
    if hours or minutes or seconds or not days:
        out += "T"
        if hours:
            out += f"{hours}H"
        if minutes:
            out += f"{minutes}M"
        if seconds or (not hours and not minutes):
            out += f"{seconds}S"
    return out


def event_lines(event):
    lines = ["BEGIN:VEVENT",
             "UID:" + escape(event["uid"]),
             "DTSTAMP:" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
             "SUMMARY:" + escape(event["summary"]),
             "DTSTART" + stamp(event["start"], event["all_day"])]

    if event["end"]:
        lines.append("DTEND" + stamp(event["end"], event["all_day"]))

    if event["description"]:
        lines.append("DESCRIPTION:" + escape(event["description"]))
    if event["location"]:
        lines.append("LOCATION:" + escape(event["location"]))
    if event["url"]:
        lines.append("URL:" + escape(event["url"]))
    if event["organizer"]:
        lines.append("ORGANIZER:mailto:" + event["organizer"])

    for person in event["attendees"]:
        prefix = "ATTENDEE;PARTSTAT=" + person["partstat"]
        if person["name"]:
            prefix += ';CN="' + str(person["name"]).replace('"', "'") + '"'
        lines.append(prefix + ":mailto:" + person["email"])

    if event["rrule"]:
        lines.append("RRULE:" + event["rrule"])
    for excluded in event["exdates"]:
        lines.append("EXDATE" + stamp(excluded, event["all_day"]))

    for offset in event["alarms"]:
        lines += ["BEGIN:VALARM",
                  "ACTION:DISPLAY",
                  "DESCRIPTION:" + escape(event["summary"]),
                  "TRIGGER:" + duration(offset),
                  "END:VALARM"]

    lines.append("END:VEVENT")
    return lines


def write_ics(path, calendar_name, color, events):
    lines = ["BEGIN:VCALENDAR",
             "VERSION:2.0",
             "PRODID:-//iPhone Calendar Rescue//EN",
             "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH",
             "X-WR-CALNAME:" + escape(calendar_name)]
    if color:
        lines.append("X-APPLE-CALENDAR-COLOR:" + str(color))
    for event in events:
        lines += event_lines(event)
    lines.append("END:VCALENDAR")

    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write("\r\n".join(fold(line) for line in lines) + "\r\n")


def safe_filename(name, taken):
    cleaned = "".join(c if (c.isalnum() or c in " -_") else "_"
                      for c in (name or "").strip()).strip() or "Calendar"
    cleaned = " ".join(cleaned.split())[:60]
    candidate, counter = cleaned, 2
    while candidate.lower() in taken:
        candidate = f"{cleaned} ({counter})"
        counter += 1
    taken.add(candidate.lower())
    return candidate + ".ics"


def write_overview(path, calendars):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Calendar", "Title", "Starts", "Ends", "All day",
                         "Location", "Repeats", "Reminders", "Notes"])
        for calendar in calendars:
            for event in sorted(calendar["events"], key=lambda e: e["start"]):
                writer.writerow([
                    calendar["name"], event["summary"],
                    event["start"].strftime("%Y-%m-%d %H:%M"),
                    event["end"].strftime("%Y-%m-%d %H:%M") if event["end"] else "",
                    "yes" if event["all_day"] else "",
                    event["location"] or "",
                    "yes" if event["rrule"] else "",
                    len(event["alarms"]) or "",
                    (event["description"] or "").replace("\n", " ")[:200],
                ])


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="calendar_rescue.py",
        description="Turn an iPhone backup into .ics calendar files.",
        epilog="Examples:\n"
               "  python3 calendar_rescue.py\n"
               "  python3 calendar_rescue.py ~/Desktop/Calendar.sqlitedb\n"
               "  python3 calendar_rescue.py ~/Desktop/my-backup -o ~/Desktop/out\n",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", help=
                        "your backup folder, or a Calendar.sqlitedb file. "
                        "Leave empty to search this computer for backups.")
    parser.add_argument("-o", "--output", help=
                        "where to put the calendar files "
                        "(default: a new folder on your Desktop)")
    parser.add_argument("--one-file", action="store_true",
                        help="only write the single combined calendar file")
    parser.add_argument("--skip", metavar="TEXT", action="append", default=[],
                        help="leave out events whose title starts with TEXT "
                             "(can be used more than once)")
    parser.add_argument("--quiet", action="store_true", help="print less")
    parser.add_argument("--version", action="version",
                        version=f"iPhone Calendar Rescue {__version__}")
    return parser


def default_output_dir():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    base = desktop if os.path.isdir(desktop) else os.getcwd()
    return os.path.join(base, "Rescued Calendars " +
                        datetime.now().strftime("%Y-%m-%d"))


def main(argv=None):
    global QUIET
    args = build_parser().parse_args(argv)
    QUIET = args.quiet

    say("=" * 62)
    say(" iPhone Calendar Rescue")
    say("=" * 62)

    output_dir = os.path.expanduser(args.output) if args.output else default_output_dir()
    workdir = os.path.join(output_dir, "_calendar_database")

    step(1, "Looking for your calendar...")
    database = resolve_input(args.path, workdir)
    say(f"  calendar database: {database}")

    step(2, "Reading your events...")
    calendars, quirks = read_calendar(database)
    total = sum(len(c["events"]) for c in calendars)
    if total == 0:
        die("The calendar database was read, but it contains no events.",
            "If this backup was made AFTER your calendar disappeared, the loss"
            " is already part of it. Try an older backup if you have one.",
            "If the phone used iCloud Calendar, the events may live online"
            " only. Sign in at icloud.com and export from there instead.")
    say(f"  {total} events in {len(calendars)} calendar(s)")

    if args.skip:
        removed = 0
        for calendar in calendars:
            keep = []
            for event in calendar["events"]:
                if any(event["summary"].startswith(s) for s in args.skip):
                    removed += 1
                else:
                    keep.append(event)
            calendar["events"] = keep
        calendars = [c for c in calendars if c["events"]]
        total -= removed
        say(f"  left out {removed} event(s) you asked to skip")

    step(3, "Writing calendar files...")
    os.makedirs(output_dir, exist_ok=True)

    everything = [e for c in calendars for e in c["events"]]
    combined = os.path.join(output_dir, "ALL EVENTS (one file).ics")
    write_ics(combined, "Rescued Calendar", None, everything)
    say(f"  {len(everything):6d}  ALL EVENTS (one file).ics")

    if not args.one_file:
        taken = set()
        for calendar in calendars:
            filename = safe_filename(calendar["name"], taken)
            write_ics(os.path.join(output_dir, filename),
                      calendar["name"], calendar["color"], calendar["events"])
            say(f"  {len(calendar['events']):6d}  {filename}")

    write_overview(os.path.join(output_dir, "Overview (open in Excel).csv"), calendars)

    if quirks["ancient"]:
        warn(f"{quirks['ancient']} birthday-style events have no real year and "
             f"show up in the year 1604. That is how the iPhone stores a "
             f"birthday without a year.")

    say("\n" + "=" * 62)
    say(" Done. Your calendars are here:")
    say(f"   {output_dir}")
    say("=" * 62)
    say("\nHow to get them onto your iPhone:")
    say("  1. Email the .ics file to yourself as an attachment.")
    say("  2. Open the email ON YOUR IPHONE and tap the attachment.")
    say("  3. Tap 'Add All' and choose which calendar to add them to.")
    say("\nThis works far better than any other method on iPhone.")
    say("\nOn a computer, import the .ics file into Apple Calendar,")
    say("Google Calendar or Outlook - always into a NEW, empty calendar,")
    say("so you can delete it in one click if it looks wrong.")
    if os.path.isdir(workdir):
        say(f"\nThe calendar database copied out of your backup is in:")
        say(f"   {workdir}")
        say("It contains personal data - delete it when you are finished.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(130)
