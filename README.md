# CalendarSave

Extract the calendar out of an iOS/iPhone backup and turn it into a standard
`.ics` file you can import into any calendar app (Apple Calendar, Google
Calendar, Outlook, Thunderbird …), plus a `.csv` for inspection in a
spreadsheet.

The source is the `Calendar.sqlitedb` database that iOS keeps in the backup —
no jailbreak, no iCloud access, no Apple ID required. Everything runs locally.

---

## How it works

```
 iPhone backup                Calendar.sqlitedb
 (iTunes/Finder)   ───────►   (SQLite, Apple epoch)
                                     │
                                     │  calendar_save.py
                                     ▼
                     apple_calendar_full_export.ics   ← everything in one file
                     apple_calendar_export.csv        ← flat overview
                     calendars/<name>.ics             ← one file per calendar
                                     │
                                     │  remove_timer_events.py  (optional)
                                     ▼
                     apple_calendar_filtered.ics      ← without "TIMER:" events
```

Two scripts, run in order:

| Script | Reads | Writes |
|---|---|---|
| `calendar_save.py` | `Calendar.sqlitedb` | `apple_calendar_full_export.ics`, `apple_calendar_export.csv`, `calendars/<name>.ics` |
| `remove_timer_events.py` | `apple_calendar_full_export.ics` | `apple_calendar_filtered.ics` |

`calendar_save.py` optionally takes the database and an output directory as
arguments; with no arguments it uses the defaults above, in the current
directory:

```bash
python calendar_save.py                              # Calendar.sqlitedb -> .
python calendar_save.py Calendar_2.sqlitedb out/     # any db, any output dir
```

`remove_timer_events.py` still takes its paths from the `INPUT_ICS` /
`OUTPUT_ICS` constants at the top of the file.

---

## 1. Setup

Requires Python 3.12+ and two packages: [`ics`](https://pypi.org/project/ics/)
0.7.x and `pytz`.

```bash
# with Poetry (pyproject.toml is already set up)
poetry install
poetry shell

# or with a plain venv
python3 -m venv .venv
.venv/bin/pip install "ics>=0.7.2,<0.8" pytz
```

> The pinned `ics` 0.7.x API is what the scripts are written against
> (`Calendar()`, `cal.events.add()`, `f.writelines(cal)`). `ics` 0.8 changes
> these — do not upgrade without adapting the code.

---

## 2. Get `Calendar.sqlitedb` out of the backup

Make a local backup of the iPhone first (Finder on macOS, or iTunes on
Windows). Backups live in:

- **macOS:** `~/Library/Application Support/MobileSync/Backup/<device-id>/`
- **Windows:** `%APPDATA%\Apple Computer\MobileSync\Backup\<device-id>\`

Inside the backup, files are stored under hashed names, not their real paths.
The calendar database is always:

| | |
|---|---|
| Domain | `HomeDomain` |
| Path in the domain | `Library/Calendar/Calendar.sqlitedb` |
| File in the backup | `2041457d5fe04d39d0ab481178355df6781e6858` (in subfolder `20`) |

That hash is the SHA-1 of `HomeDomain-Library/Calendar/Calendar.sqlitedb` and
is the same on every device, so you can copy it straight out:

```bash
cp ~/Library/Application\ Support/MobileSync/Backup/<device-id>/20/2041457d5fe04d39d0ab481178355df6781e6858 \
   ./Calendar.sqlitedb
```

Notes:

- **Encrypted backups** store the file encrypted. Decrypt the backup first with
  a tool such as `iphone-backup-decrypt`, `iOSbackup` (Python) or iMazing, then
  take `Calendar.sqlitedb` from the decrypted output.
- If a `Calendar.sqlitedb-wal` / `-shm` sidecar exists next to the database,
  copy those too — SQLite needs them to see the most recent writes.
- Work on a **copy**. The scripts only read, but there is no reason to point
  them at your only backup.

---

## 3. Export

```bash
python calendar_save.py
```

```
Found 5871 calendar items in database
✅ Exported 5871 events to apple_calendar_full_export.ics
✅ Exported 5871 events to apple_calendar_export.csv
```

Every row of `CalendarItem` that has a `start_date` becomes one `VEVENT`.
Apple stores timestamps as seconds since **2001-01-01 UTC**; the script
converts them to real datetimes and shifts them into each event's own
`start_tz` timezone. All-day events are written as date-only `VALUE=DATE`
entries so they don't drift across midnight.

### Per-calendar files

Alongside the combined export, the script writes one `.ics` per source calendar
into `calendars/`, and prints the breakdown:

```
    5812  DEFAULT_CALENDAR_NAME.ics
     156  Scheduled_Reminders.ics
     148  Deutsche_Feiertage.ics
     134  Geburtstage.ics
      23  Nordrhein-Westfalen_Schulferien_-_Schulferien.ics
       ...
✅ Exported 9 calendars to ./calendars/
```

Each file carries an `X-WR-CALNAME` header, so it imports under its real
calendar name ("Deutsche Feiertage") rather than the sanitized file name.
Import these instead of the combined file when you want your calendars to stay
separate and individually colourable. Two calendars with the same title (a
duplicated subscription, say) get the calendar's row id appended —
`Alaska_Airlines.ics` and `Alaska_Airlines_23.ics` — so neither is lost.

### Optional: drop "TIMER:" events

The sample data contains a few hundred auto-generated events whose title starts
with `TIMER:`. To get a calendar without them:

```bash
python remove_timer_events.py
```

```
Found 5871 events in total
   Original events: 5871
   TIMER events removed: 264
   Remaining events: 5607
   Output file: apple_calendar_filtered.ics
```

To filter on a different prefix, change the `startswith("TIMER:")` check in
`remove_timer_events.py`.

---

## 4. Import the calendar

The resulting `.ics` is a plain iCalendar file:

- **Apple Calendar (macOS):** File → Import…, pick the `.ics`, and choose
  **New Calendar** as the target so the import stays separate from your
  existing events.
- **Google Calendar:** Settings → Import & export → Import, select the file
  and the destination calendar.
- **Outlook / Thunderbird:** File → Open & Export → Import an iCalendar (.ics)
  file / Events and Tasks → Import.

Import into a *new, empty* calendar the first time. With ~6 000 events, undoing
a merge into your main calendar is painful; deleting a whole calendar is one
click.

To keep your calendars separate, import each file in `calendars/` into its own
new calendar instead of importing the combined export.

---

## What ends up in the export

Per event, from `CalendarItem` and its related tables:

| iCalendar field | Source |
|---|---|
| `UID` | `CalendarItem.UUID` |
| `SUMMARY` | `CalendarItem.summary` (falls back to `Untitled Event`) |
| `DESCRIPTION` | `CalendarItem.description` |
| `DTSTART` / `DTEND` | `start_date` / `end_date`, Apple epoch → `start_tz` |
| all-day | `CalendarItem.all_day` → date-only `DTSTART` |
| `LOCATION` | `Location.title` via `location_id` |
| `ORGANIZER` | `Identity.address` via `organizer_id` (`MAILTO:` stripped) |
| `X-WR-CALNAME` | `Calendar.title` via `calendar_id` (per-calendar files only) |

`apple_calendar_export.csv` carries the same events as one row each, with the
columns: UID, Calendar, Title, Start Date, End Date, All Day, Location,
Description (truncated to 200 chars), Timezone, Organizer, Has Recurrence,
Alarm Count, Attendee Count.

---

## Known limitations

These are real, verified against the sample database — check them before
trusting the export as a complete archive.

- **Recurring events are flattened.** 528 events in the sample database have
  recurrence rules, but the export contains **no `RRULE` lines** — each
  recurring series appears only as its single master occurrence. The
  `Recurrence` / `ExceptionDate` tables are queried, and the `FREQ`,
  `INTERVAL`, `COUNT`, `UNTIL` values are assembled in code, but `ics` 0.7
  cannot serialize them via the `extra` field, so they are dropped. Repeating
  appointments will not repeat after import.
- **No alarms / reminders.** The `Alarm` lookup queries a column
  (`trigger` / `owner_id`) that does not exist in this schema — the real
  columns are `trigger_interval` and `calendaritem_owner_id` — so the query
  always fails, is swallowed by the `except`, and `Alarm Count` is always `0`.
  No `VALARM` blocks are written.
- **No attendees.** Likewise there is no `Attendee` table, and the `Participant`
  fallback selects a non-existent `display_name` column, so `Attendee Count` is
  always `0` and no `ATTENDEE` lines are emitted.
- **Calendar colours are not preserved.** The events are split per calendar
  (see above) and each file keeps its name, but `Calendar.color` is not read,
  so your calendar app assigns fresh colours on import. Note that the combined
  `apple_calendar_full_export.ics` is still one flat calendar by design — use
  the `calendars/` files if you want the split.
- **Only events, no reminders.** The export takes every row with a
  `start_date`; in the sample database all 5 871 rows are `entity_type = 2`
  (events). Reminders/tasks are not handled specially.
- **Unknown timezones fall back to UTC**, including the `_float` marker Apple
  uses for floating times (894 events in the sample) — these are mostly all-day
  entries, where it doesn't matter.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `sqlite3.OperationalError: no such column: …` | The schema differs between iOS versions. Run `python inspect_db.py` to dump the actual columns and adjust the query. |
| `AttributeError: 'tuple' object has no attribute 'clone'` | Something was appended to `Event.extra` that `ics` cannot serialize (this is why RRULE/ATTENDEE support is commented out). |
| `sqlite3.DatabaseError: file is not a database` | The backup is encrypted — decrypt it before extracting the file. |
| Export has far fewer events than expected | The `-wal` sidecar was not copied, so recent writes are missing. |
| Import silently does nothing | Some apps reject an `.ics` over a size limit; import `apple_calendar_filtered.ics`, or split it. |

---

## Files in this repo

| File | Purpose |
|---|---|
| `calendar_save.py` | Main export: SQLite → `.ics` + `.csv` |
| `remove_timer_events.py` | Post-filter: strips `TIMER:` events from an `.ics` |
| `inspect_db.py` | Dumps `Recurrence`, `ExceptionDate`, `Identity`, `Participant` schemas + samples |
| `check_identity.py` | Dumps just the `Identity` table |
| `db_schema.txt`, `identity_schema.txt` | Saved output of the inspection scripts |
| `*_run.txt`, `output*.txt` | Saved console logs from earlier runs |
| `Calendar.sqlitedb` | The extracted backup database (personal data — keep out of version control) |
| `apple_calendar_*.ics` / `.csv` | Generated exports (personal data) |
| `calendars/` | Generated per-calendar exports (personal data) |

The database and the exports contain real personal calendar data. If this
directory ever becomes a git repository, add a `.gitignore` for
`Calendar.sqlitedb*`, `*.ics`, `*.csv` and the export directories first.
