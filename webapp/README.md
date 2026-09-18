# The web version — how to host it on your own domain

This folder is a **complete, self-contained website**. Three files, no server,
no database, no backend, no Python. The conversion happens inside the visitor's
own browser.

```
index.html      the page (the whole tool)
sql-wasm.js     SQLite compiled for the browser  ) sql.js 1.14.2
sql-wasm.wasm   the SQLite engine itself         ) MIT licence
fonts/          the three typefaces               ) SIL OFL 1.1
```

**The page loads nothing from anyone else at runtime** — no CDN, no Google
Fonts, no analytics. Everything it needs is in this folder. That is what makes
"your file never leaves your device" true of the whole page and not just of the
calendar data.

**The source is in the repository on purpose.** This page asks people to hand
it their entire personal calendar, so the least it can do is let them read
exactly what it does with it — `index.html` is one readable file, and there is
no build step, no bundler and no minification between what is published here
and what runs in the browser. Suggestions and corrections are welcome.

---

## Try it before you host it

You can run the page on your own machine in one command. From inside this
folder:

```bash
python3 -m http.server 8000      # Mac / Linux
python  -m http.server 8000      # Windows
```

Then open **http://localhost:8000** in your browser. That is the real thing,
running locally — convert a file, watch the network tab, confirm for yourself
that nothing is sent anywhere.

> It must be served over `http://`, not opened as a `file://` path: browsers
> refuse to load WebAssembly from the filesystem.

---

## Checking the SQLite files are genuine

`sql-wasm.js` and `sql-wasm.wasm` are [sql.js](https://github.com/sql-js/sql.js)
1.14.2, MIT licensed, copied here unmodified so the page does not have to load
anything from a third party at runtime.

You do not have to trust that. Verify it:

```bash
shasum -a 256 sql-wasm.js sql-wasm.wasm       # Mac / Linux
certutil -hashfile sql-wasm.wasm SHA256       # Windows
```

You should get exactly:

```
f1c84000dbc856c9d87f4f3aabc4d3654bd436165db4be3da13751db3a9c20d7  sql-wasm.js
38c14f6e379210bc942bdc4ebca44e7bfdb4318ecc1c72ca666a28fdce96670a  sql-wasm.wasm
```

which is what you get from the official package:

```bash
curl -sO https://cdn.jsdelivr.net/npm/sql.js@1.14.2/dist/sql-wasm.js
curl -sO https://cdn.jsdelivr.net/npm/sql.js@1.14.2/dist/sql-wasm.wasm
```

---

## What you actually need

**Requirements: a static file host and a domain. That is the entire list.**

| You need | You do *not* need |
|---|---|
| Somewhere to put 3 files | A server or VPS |
| A domain name (you have one) | Python, Node, PHP, a database |
| HTTPS (free everywhere) | An email provider |
| An Impressum + privacy page | Cookie banner, user accounts, GDPR consent flow |

Because no data ever reaches you, this is **cheap and legally simple**. That is
not a small detail — see [Why there is no email option](#why-there-is-no-email-option).

---

## Option A — Cloudflare Pages (recommended, free)

Best bandwidth, cleanest domain setup, free TLS.

1. Create a free account at [pages.cloudflare.com](https://pages.cloudflare.com).
2. **Create a project → Direct Upload**, name it `calendar-rescue`.
3. Drag this whole folder into the upload area. Deploy.
4. **Custom domains → Set up a domain** → enter `calendar.yourdomain.de`.
   - If your domain's DNS is already at Cloudflare, it adds the record itself.
   - If not, add the `CNAME` record it shows you at your current DNS provider.
5. TLS is issued automatically within a few minutes.

## Option B — GitHub Pages (free)

1. Make a new repository, e.g. `calendar-rescue-web`, and upload these 3 files.
2. **Settings → Pages →** source `main`, folder `/ (root)`.
3. **Settings → Pages → Custom domain →** `calendar.yourdomain.de`, tick
   *Enforce HTTPS*.
4. At your DNS provider add a `CNAME` for `calendar` pointing to
   `sarahvgls.github.io`.

Works fine — the page needs no special HTTP headers, which is the usual reason
GitHub Pages fails for WebAssembly projects.

## Option C — your own webspace

If your domain already comes with normal hosting, just upload the three files
into a folder in the webroot, e.g. `/calendar/`, and visit
`https://yourdomain.de/calendar/`.

Only requirement: **`.wasm` must be served as `application/wasm`.** Most servers
do this already. If the page hangs at "Reading your events…", that is the cause.
On Apache, add a `.htaccess`:

```apache
AddType application/wasm .wasm
```

On nginx, in `mime.types`: `application/wasm wasm;`

---

## Must it be HTTPS?

Technically no — the file picker and WebAssembly both work over plain HTTP. But
serve HTTPS anyway. The entire promise of this page is *"your calendar never
leaves your device"*, and that claim is hard to take seriously on an
unencrypted connection. Every option above gives you free TLS.

---

## The legal side (Germany)

*Not legal advice — but the shape of the problem is worth understanding.*

Because the calendar file is read **in the visitor's browser and never
transmitted**, you are not processing their personal data at all. There is
nothing to store, nothing to delete, nothing to breach. That removes essentially
the whole GDPR burden.

What still applies, because you are running a website:

- **Impressum** — required under **§ 5 DDG**. (The TMG was replaced by the
  Digitale-Dienste-Gesetz in May 2024; an Impressum still citing "§ 5 TMG" is a
  common target for Abmahnungen.)
- **Datenschutzerklärung** — short, but needed: your host logs visitor IP
  addresses, and IPs count as personal data.
- **AVV / DPA with your hosting provider** — Cloudflare and GitHub both offer
  standard ones.

Two things to keep it that way:

1. **Do not add analytics or error reporting.** The moment a script reports
   filenames or file contents back to you, the "nothing leaves your device"
   claim stops being true and the GDPR obligations return.
2. **Keep the sql.js files and the fonts local** (as they are here) rather than
   loading them from a CDN. Loading anything from a third party transmits your
   visitors' IP addresses to that third party, which needs a legal basis and
   typically a notice under **§ 25 TDDDG**. This is not hypothetical for fonts:
   the Landgericht München ruled in January 2022 that embedding Google Fonts
   dynamically violates the GDPR, and a wave of Abmahnungen followed. The page
   ships its own fonts for exactly this reason — see
   [`fonts/README.md`](fonts/README.md).

---

## Why there is no email option

You wanted to offer emailing the result. It is deliberately left out, and the
reason is worth stating plainly.

Sending the calendar by email means the calendar has to reach your server
first. Calendars routinely contain doctor's appointments, therapy sessions,
religious holidays and union meetings — **special-category data under GDPR
Article 9**, where processing is *prohibited* unless a narrow exception applies.
The realistic route is explicit, unbundled consent naming those exact
categories. On top of that: a record of processing activities (the small-company
exemption does not apply to Art. 9 data), a data processing agreement with the
email provider, a probable DPIA, a retention and deletion policy, and 72-hour
breach notification duties.

All of that — plus a monthly server bill — to replace a button the browser
already provides for free.

The page tells users to **download the file and email it to themselves**, which
gets the same result with none of the liability. Your own experience that
"email works best on iPhone" still holds — it is the *user* sending the mail,
not you.

---

## What about uploading a whole backup?

Also deliberately not offered. A full iPhone backup is **5–100 GB** across tens
of thousands of files, and contains messages, photos, health records and
keychain data. Uploading all of that to read one ~10 MB calendar file would be
a bad trade for the user and an enormous liability for you.

The page does let people pick their **backup folder** — but that folder is read
locally by their own browser, which pulls out only the calendar. Nothing is
uploaded.

---

## Updating the page later

Re-upload `index.html`. The sql.js files only change if you deliberately update
them.

To keep them current, download fresh copies:

```bash
curl -O https://cdn.jsdelivr.net/npm/sql.js@1.14.2/dist/sql-wasm.js
curl -O https://cdn.jsdelivr.net/npm/sql.js@1.14.2/dist/sql-wasm.wasm
```
