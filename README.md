# iPhone Calendar Rescue

**Lost your calendar? If you have an iPhone backup on your computer, your
appointments may well still be in it. This gets them back out.**

It takes an iPhone backup and produces `.ics` files — the standard calendar
format that Apple Calendar, Google Calendar, Outlook and everything else can
import. You get one file per calendar, so "Birthdays" stays separate from
"Work".

You do not need to know how to code. You need to copy one command and paste
one file path. That is the whole job.

---

## ⚡ The quickest way: use it in your browser

**There is a web version that needs no installation at all.** You open a page,
choose your file, and download your calendars. It runs entirely inside your own
browser — nothing is uploaded, and there is no server involved.

> ### 👉 https://calendar.example.com
>
> <!-- REPLACE the line above with your own address once the page is live.
>      The three files that make up that page, and step-by-step hosting
>      instructions, are in the webapp/ folder of your local copy. -->

For most people that is the whole answer, and you can stop reading here. Carry
on below if you would rather run it on your own computer, if you have thousands
of events and want the command line version, or if you want to see exactly what
it does.

---

## 🤖 A note for human readers

**If reading instructions is not your idea of a good time, hand this problem to
an AI assistant instead.** Tools like Claude, ChatGPT or Copilot are genuinely
good at exactly this kind of task, and some of them can run the commands for
you rather than just telling you about them.

Open one of them and say something like:

> I lost my iPhone calendar but I have an iTunes backup on my computer.
> Please help me use https://github.com/sarahvgls/iphone-calendar-rescue
> to get my appointments back as .ics files. Walk me through it one step
> at a time, and assume I am not a programmer.

If you are using an AI assistant with access to your computer (Claude Code,
for example), you can simply point it at this repository and ask it to do the
whole thing. It will read the instructions below, find your backup, run the
tool and tell you where your calendar files are. That is not cheating — it is
the fastest route, and this tool was built that way itself.

### If you are an AI agent reading this

Most of the instructions below exist to walk a human through a terminal. **If
you can run commands yourself, skip that choreography** — where to save the
file, how to open Terminal, how to paste a path. None of it matters to you.
What does:

- **Run `calendar_rescue.py` directly from wherever you cloned it**, with any
  path and any output directory. It needs Python 3.8+ and nothing else — no
  `pip install`, no virtualenv. `--help` lists the options.
- **Prefer the user's oldest backup, not the newest**, and say why. See
  [Will this actually work for me?](#-will-this-actually-work-for-me). If one
  backup yields nothing, try an older one before concluding it failed.
- **Warn before any new backup is made** — it can overwrite the older backup
  that still holds the data.
- **Treat every file involved as confidential.** The database and the `.ics`
  output are the user's entire personal calendar: medical appointments,
  relationships, travel. Do not upload them, do not paste their contents into
  a chat log, a bug report or a commit. Work locally.
- **Do not attempt to script iTunes Backup Explorer.** It is a GUI-only Java
  application with no command line interface; its `main()` discards its
  arguments. If a backup is encrypted, hand the manual steps to the user.
- **Finish the job:** tell the user where the files are and that emailing an
  `.ics` to themselves is the most reliable way onto an iPhone.

---

## ⚠️ Will this actually work for me?

**Honest answer: it is worth trying, but nothing here can promise success.** It
depends on *when* your backup was made.

A backup is a snapshot of one moment. This tool reads what is in that snapshot —
it cannot recover anything the snapshot does not contain.

| Your backup was made… | Your chances |
|---|---|
| **Before** the calendar disappeared | **Good.** The events should be in there. |
| **After** the calendar disappeared | **Poor, but still worth a try.** The snapshot may already contain the loss. |
| You are not sure | Try it. It costs you ten minutes and changes nothing. |

So: **use the oldest backup you have**, not the newest. If the tool finds
nothing useful in one backup, try an older one.

> ### 🛑 Before you make a new backup, read this
>
> Making a fresh backup can **overwrite the older backup on your computer** —
> the very one that might still contain your events. If you already have a
> backup from before your calendar vanished, **copy that backup folder
> somewhere safe first** (an external drive, another folder, anywhere). Then
> experiment as much as you like.
>
> Backup folders are large (several GB) but copying one is just a normal file
> copy. It is the single most important step on this page.

Even in the good case, nothing is guaranteed: calendars that lived in iCloud
were often never written into the local backup at all. The
[troubleshooting section](#if-something-goes-wrong) covers that.

---

## Table of contents

- [Will this actually work for me?](#-will-this-actually-work-for-me)
- [The quickest way: use it in your browser](#-the-quickest-way-use-it-in-your-browser)
- [Before you start](#before-you-start)
- [Step 1 — Install Python](#step-1--install-python)
- [Step 2 — Make an iPhone backup](#step-2--make-an-iphone-backup)
- [Step 3 — Download this tool](#step-3--download-this-tool)
- [Step 4 — Run it](#step-4--run-it)
- [Step 5 — Put the calendar back on your iPhone](#step-5--put-the-calendar-back-on-your-iphone)
- [The privacy-friendly route](#the-privacy-friendly-route-export-only-the-calendar-file)
- [If something goes wrong](#if-something-goes-wrong)
- [What you get](#what-you-get)
- [Honest limitations](#honest-limitations)
- [About this project](#about-this-project)

---

## Before you start

**How long does this take?** About 15 minutes, most of which is waiting for the
backup to finish.

**What you need:**

- A computer (Mac or Windows) with an iPhone backup on it, **or** your iPhone
  so you can make a fresh backup.
- Python installed (Step 1 — it is free and takes two minutes).
- That is it. No accounts, no payment, nothing to sign up for.

**Does my data leave my computer?** No. Everything happens locally on your own
machine. This tool has no internet connection of any kind — it cannot upload
anything even if it wanted to.

**A word about the backup password.** If your backup is *encrypted*, this tool
cannot read it, and neither can anything else without the password. Step 2
explains how to make an unencrypted backup. If you have an encrypted backup and
you know the password, see [the privacy-friendly route](#the-privacy-friendly-route-export-only-the-calendar-file).

---

## Step 1 — Install Python

Python is a free program that runs tools like this one. You install it once and
then forget about it.

### On a Mac

Macs usually have it already. To check, open **Terminal**:

1. Press `Cmd` + `Space`, type `Terminal`, press `Enter`.
2. In the black (or white) window that opens, type this and press `Enter`:

   ```bash
   python3 --version
   ```

If you see something like `Python 3.12.4`, you are done — skip to Step 2.

If you see an error, or a box pops up asking to install "command line developer
tools", click **Install** and wait. Alternatively download Python from
[python.org/downloads](https://www.python.org/downloads/) and run the installer.

### On Windows

1. Go to [python.org/downloads](https://www.python.org/downloads/) and click the
   big yellow **Download Python** button.
2. Run the file you downloaded.
3. **IMPORTANT:** on the first screen of the installer, tick the box at the
   bottom that says **"Add python.exe to PATH"**. It is easy to miss and
   nothing will work without it.
4. Click **Install Now** and wait.

To check it worked, press the `Windows` key, type `cmd`, press `Enter`, then
type:

```
python --version
```

You should see a version number.

> **Throughout this guide:** Mac users type `python3`, Windows users type
> `python`. That is the only difference.

---

## Step 2 — Make an iPhone backup

**Already have a backup on this computer? Skip to Step 3** — the tool will
usually find it by itself, and you can always point it at the folder yourself.

⚠️ **First read the warning above about overwriting an older backup.** If you
already have a backup from before your calendar disappeared, copy it somewhere
safe before making a new one.

### Important: turn OFF backup encryption first

An encrypted backup is scrambled and cannot be read without the password. If
you want the simple route, make an unencrypted backup:

### On a Mac (macOS Catalina 10.15 or newer)

1. Connect your iPhone with a cable.
2. Open **Finder**. Your iPhone appears in the left sidebar under *Locations*.
   Click it.
3. Choose **"Back up all of the data on your iPhone to this Mac"**.
4. **Untick "Encrypt local backup"** if it is ticked. (It may ask for your
   existing password to turn it off. If you do not know it, use
   [the privacy-friendly route](#the-privacy-friendly-route-export-only-the-calendar-file)
   instead.)
5. Click **Back Up Now** and wait until it finishes.

### On Windows

1. Install the **Apple Devices** app from the Microsoft Store (on older systems
   this is **iTunes**).
2. Connect your iPhone with a cable and open the app.
3. Click your iPhone, then **General** (or *Summary* in iTunes).
4. Choose **"Back up all of the data on your iPhone to this computer"**.
5. **Untick "Encrypt local backup"**.
6. Click **Back Up Now** and wait.

Backups can take anywhere from a few minutes to an hour. Let it finish
completely.

---

## Step 3 — Download this tool

You only need one file: **`calendar_rescue.py`**.

**The easy way:**

1. Go to
   [calendar_rescue.py](https://github.com/sarahvgls/iphone-calendar-rescue/blob/main/calendar_rescue.py).
2. Click the **download icon** (a downward arrow) near the top right of the
   file view.
3. Save it to your **Desktop**.

That is the only file you need. It is plain text — you are welcome to open it
in any text editor and read exactly what it does.

---

## Step 4 — Run it

Open **Terminal** (Mac) or **Command Prompt** (Windows), as in Step 1.

Type this and press `Enter`:

**Mac:**
```bash
cd ~/Desktop
python3 calendar_rescue.py
```

**Windows:**
```
cd %USERPROFILE%\Desktop
python calendar_rescue.py
```

That is it. With no other instructions, the tool searches your computer for
iPhone backups, picks the most recent one, and writes your calendars to a new
folder on your Desktop called **"Rescued Calendars"**.

You should see something like this:

```
==============================================================
 iPhone Calendar Rescue
==============================================================

[1] Looking for your calendar...
  using your most recent backup: Sarahs iPhone - 01 September 2026
  found Calendar.sqlitedb  (7.7 MB)

[2] Reading your events...
  5871 events in 16 calendar(s)

[3] Writing calendar files...
    5871  ALL EVENTS (one file).ics
    4904  Kalender.ics
     264  Birthdays.ics
     148  Holidays.ics
     ...

==============================================================
 Done. Your calendars are here:
   /Users/you/Desktop/Rescued Calendars 2026-09-18
==============================================================
```

### If you have the calendar file already

If someone gave you a `Calendar.sqlitedb` file, or you exported one yourself
(see [the privacy-friendly route](#the-privacy-friendly-route-export-only-the-calendar-file)),
point the tool at it instead:

**Mac:**
```bash
python3 calendar_rescue.py /path/to/Calendar.sqlitedb
```

> **Tip:** you do not have to type the path. Type `python3 calendar_rescue.py `
> (with a space at the end), then **drag the file from Finder into the Terminal
> window**. The path appears by itself. Then press `Enter`.

**Windows:**
```
python calendar_rescue.py C:\path\to\Calendar.sqlitedb
```

> **Tip:** drag the file onto the Command Prompt window to paste its path.

### Extra options (you probably do not need these)

| Option | What it does |
|---|---|
| `-o FOLDER` | Put the results somewhere other than the Desktop |
| `--one-file` | Only write the single combined calendar, no per-calendar files |
| `--skip "TIMER:"` | Leave out events whose title starts with `TIMER:` |
| `--quiet` | Print less |
| `--help` | Show all options |

---

## Step 5 — Put the calendar back on your iPhone

### 📧 The best way: email it to yourself

This sounds primitive. It is also, by a wide margin, the most reliable way to
get a calendar onto an iPhone.

1. On your computer, write yourself an email and **attach** one of the `.ics`
   files. Start with a small one to test — e.g. `Birthdays.ics` rather than the
   big combined file.
2. Send it.
3. **Open that email on your iPhone** (in the Mail app).
4. Tap the attachment.
5. iOS shows you the events and offers **"Add All"**. Tap it.
6. Choose which calendar to add them to — **create a new one** if you can, so
   you can delete everything in one go if it looks wrong.

Repeat for each `.ics` file you want back.

> **Why email?** AirDrop, iCloud Drive and Files often open `.ics` files in a
> preview instead of offering to import them. Mail hands them to the Calendar
> app properly. If one `.ics` is too large to email, use the individual
> calendar files rather than the combined one.

### On a computer instead

- **Apple Calendar (Mac):** File → Import…, pick the `.ics`, and choose
  **New Calendar** as the destination.
- **Google Calendar:** Settings → Import & export → Import. If you import into
  Google and your iPhone already syncs with that Google account, the events
  will appear on your phone by themselves.
- **Outlook:** File → Open & Export → Import an iCalendar (.ics) file.

⚠️ **Always import into a new, empty calendar first.** If you dump several
thousand events straight into your main calendar and it looks wrong, undoing it
is genuinely painful. A separate calendar can be deleted in one click.

---

## The privacy-friendly route: export only the calendar file

Handing a whole iPhone backup to anyone — a helper, a repair shop, an AI
assistant — means handing over your messages, photos, health data and
passwords. You almost never need to.

**Your entire calendar lives in a single file inside the backup.** You can
export just that one file and share nothing else. This also works for
**encrypted backups**, as long as you know the password.

The tool for this is **iTunes Backup Explorer**, a free, open-source program.
**It works on Windows, Mac and Linux alike** — the steps below are the same on
all three, apart from one Mac-only permission step.

👉 **https://github.com/MaxiHuHe04/iTunes-Backup-Explorer**

> This is someone else's project, not part of this one. It is an ordinary
> program with a window and buttons — nothing to type into a terminal.

### Step 1 — Install it

Go to the
[Releases page](https://github.com/MaxiHuHe04/iTunes-Backup-Explorer/releases)
and download the file for your system from the newest release:

| Your system | Download the file ending in | Then |
|---|---|---|
| **Windows** | `_win_x64.msi` | Double-click it and follow the installer. |
| **Mac (Apple silicon: M1–M4)** | `_mac_arm64.dmg` | Open it and drag the app to Applications. |
| **Mac (older Intel)** | `_mac_x64.dmg` | Open it and drag the app to Applications. |
| **Linux** | `_debian_x64.deb` | Install it with your package manager. |

The Windows and Mac installers include everything they need. (On Linux you may
need Java 18 or newer separately.)

### Step 2 — Mac only: give it permission

**Skip this on Windows and Linux.**

On a Mac, go to **System Settings → Privacy & Security → Full Disk Access** and
switch **on** iTunes Backup Explorer, then quit and reopen the program. macOS
hides the backup folder from programs until you do this, and exports fail with
a permission error.

### Step 3 — Open your backup

Start the program. It looks for backups by itself and lists the ones it finds.
Click the one you want to open.

If it is encrypted, it asks for the backup password — type it, and the rest
works exactly the same.

> **If the list is empty**, that does not mean you have no backup. The program
> only looks in the standard location, and yours may be elsewhere — on another
> drive, or moved at some point. Open the program's **settings/preferences**
> and point it at the folder where your backups actually live. Once you set
> the correct path, your backups appear in the list.
>
> The usual locations are listed under
> ["No iPhone backup found"](#no-iphone-backup-found-on-this-computer) below.

### Step 4 — Find the calendar file

1. Go to the **File Search** tab.
2. In the **Domain** field, type:
   ```
   HomeDomain
   ```
3. In the **Relative Path** field, type exactly this — the `%` at the end
   matters:
   ```
   Library/Calendar/Calendar.sqlitedb%
   ```
4. Click **Search**. You should get one to three results: `Calendar.sqlitedb`
   and possibly `Calendar.sqlitedb-wal` and `Calendar.sqlitedb-shm`.

### Step 5 — Export it

Click **Export matching** and choose a folder — your Desktop is fine.
(To export just one row instead, right-click it and choose **Extract**.)

> **Take all of the files it finds, not just the first one.** On iOS 17.4 and
> newer, some of your most recent events can live in the `-wal` file. If you
> export only `Calendar.sqlitedb`, those events go missing silently.

### Step 6 — Convert it

Point this tool at the folder you exported into:

```bash
python3 calendar_rescue.py ~/Desktop/the-folder-you-exported-to    # Mac / Linux
python  calendar_rescue.py %USERPROFILE%\Desktop\the-folder       # Windows
```

Or simply drop that file into the [web version](#-the-quickest-way-use-it-in-your-browser),
which needs no installation at all.

Nothing but your calendar ever leaves the backup.

---

## If something goes wrong

The tool tries to explain problems in plain language rather than showing an
error message. Here are the common ones.

### "macOS will not let this script read…"

macOS protects the backup folder. This is a system setting, not a broken
backup.

1. **System Settings → Privacy & Security → Full Disk Access**
2. Switch **on** the app you are running the command from — normally
   **Terminal**.
3. **Quit Terminal completely** (`Cmd` + `Q`, not just closing the window) and
   open it again.
4. Run the command again.

### "This backup is encrypted"

An encrypted backup cannot be read without its password. Either:

- Make a fresh backup with **"Encrypt local backup" unticked** (Step 2), or
- Use [the privacy-friendly route](#the-privacy-friendly-route-export-only-the-calendar-file)
  — iTunes Backup Explorer *can* open encrypted backups if you know the
  password.

If you have forgotten the password, there is no way around it. Apple cannot
reset it either. Make a new, unencrypted backup instead.

### "No iPhone backup found on this computer"

Either there genuinely is not one (do Step 2), or it is not where the tool
looked. **Most of the time backups live in one of these places** — but not
always, since the location can be changed, and backups are often moved to an
external drive when space runs short:

| System | Usually here |
|---|---|
| Mac | `~/Library/Application Support/MobileSync/Backup/` |
| Windows (Apple Devices app / Microsoft Store iTunes) | `C:\Users\<you>\Apple\MobileSync\Backup` |
| Windows (classic iTunes) | `C:\Users\<you>\AppData\Roaming\Apple Computer\MobileSync\Backup` |

If yours is somewhere else — an external drive, a folder you moved it to, a
copy someone made for you — that is fine. Pass that folder directly:

```bash
python3 calendar_rescue.py "/path/to/that/folder"
```

You are looking for a folder whose name is a long string of letters and
numbers, containing a file called `Manifest.db`. If you are not sure which
folder is the right one, pass the folder *above* them and the tool picks the
newest.

**The same applies to iTunes Backup Explorer:** if its list of backups comes up
empty, it simply did not find them in the standard place. Set the correct path
in the program's settings/preferences and they will appear.

### "This backup does not contain a calendar database" or "no events"

The usual cause is **iCloud Calendar**. If your calendar syncs with iCloud, the
events live on Apple's servers and are not written into the local backup.

Try this instead: sign in at [icloud.com](https://www.icloud.com) → Calendar,
and export from there. On a Mac, opening Calendar.app while signed into the
same iCloud account will also pull the events down, and you can then export
them with File → Export.

### "python: command not found" / "not recognized as an internal command"

Python is not installed, or on Windows the **"Add python.exe to PATH"** box was
not ticked during installation. Reinstall it and make sure that box is ticked
(Step 1).

### The backup is very old

Backups from iOS 9 and earlier use a different, obsolete format that this tool
cannot read. You will get a clear message if that happens.

---

## What you get

Inside the output folder:

| File | What it is |
|---|---|
| `ALL EVENTS (one file).ics` | Every event from every calendar in one file |
| `<Calendar name>.ics` | One file per calendar — birthdays, holidays, work… |
| `Overview (open in Excel).csv` | A plain table of everything, to look through |
| `_calendar_database/` | The raw calendar file copied out of your backup |

> `_calendar_database/` contains your personal data in raw form. It is kept in
> case something needs re-running. **Delete it when you are finished.**

Each event keeps its title, notes, location, start and end time, all-day
status, repeat rule, reminders, attendees, organiser and web link. Each
per-calendar file remembers its own name and colour, so it imports as a proper
named calendar rather than a nameless heap.

---

## Honest limitations

- **Repeating events are converted, not simulated.** Apple's repeat rules are
  translated into the standard iCalendar equivalent. Common patterns (every
  week, every year, "last Sunday in March") come across correctly. Very exotic
  custom rules may not.
- **Birthdays without a year show up in 1604.** That is genuinely how the
  iPhone stores a birthday when it does not know the year. The tool tells you
  how many are affected. They import fine, they just look odd.
- **Times are exported in UTC.** Your calendar app converts them back to local
  time, so appointments appear at the right moment. Only the raw file looks
  unfamiliar.
- **Calendar colours are a suggestion.** Most apps honour the colour; some
  ignore it and assign their own.
- **Reminders and to-dos are not included** — only calendar events.
- **iCloud-only calendars are not in the backup at all.** See the
  troubleshooting section.

---

## About this project

### ⚠️ This is a "vibe-coded" tool

Be aware of what you are running:

**This project was written largely by an AI assistant, working from
conversational instructions. The code has been tested against real iPhone
backups and produces correct results on them, but it has not been
comprehensively reviewed line by line by a human expert, and it has no
automated test suite.**

What that means in practice:

- It is a **recovery tool, not a backup strategy.** Check that the events it
  produces actually look right before you rely on them.
- **It only ever reads your backup.** It does not modify, move or delete
  anything in it. The worst realistic outcome is an incomplete or wrong `.ics`
  file, not a damaged backup.
- **It is offline.** No network code, no telemetry, no accounts.
- If you need certainty rather than convenience, read the source — it is one
  file, written to be readable — or have someone you trust read it.

This disclosure is deliberate. Tools like this are increasingly common and
often do not say so.

### Licence

MIT — see [LICENSE](LICENSE). Use it, change it, share it, sell it, include it
in your own project. No warranty of any kind: if it does not work for you, that
is unfortunate but not something anyone is liable for.

### Contributing

Bug reports and pull requests are welcome at
[the issue tracker](https://github.com/sarahvgls/iphone-calendar-rescue/issues).
Useful things to report: an iOS version or backup layout it fails on, a repeat
rule it translates wrongly, or a confusing message.

**Never attach a real `Calendar.sqlitedb`, `.ics` export or backup to an issue.**
They contain your entire personal calendar. Describe the problem instead, or
attach a small file you have made up yourself.

### Credits

- [iTunes Backup Explorer](https://github.com/MaxiHuHe04/iTunes-Backup-Explorer)
  by Maximilian Herczegh (MIT) — the recommended way to export a single file
  from a backup, including encrypted ones.
- The iOS backup format is documented in
  [Rich Infante's write-up](https://www.richinfante.com/2017/3/16/reverse-engineering-the-ios-backup).
