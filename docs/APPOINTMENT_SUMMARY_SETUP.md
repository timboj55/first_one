# Booking summary PDF (n8n)

When a patient is booked in PracticeQ, a one-page PDF listing **all** their upcoming
appointments is uploaded to their PracticeQ client file (Files tab), **30 minutes after the
last change** to their schedule. Booking several visits in a row, or fixing a mistake
(reschedule, cancel, rebook) inside those 30 minutes, restarts the timer, so one correct PDF
is filed. The list is read fresh from PracticeQ at upload time.

It is a **separate n8n workflow**. The existing "IntakeQ Appointments -> GHL" workflow and the
PracticeQ webhook are not touched. (An email version existed briefly; it is in git history at
commit `37d6772` if email is wanted later.)

```
Every 5 minutes -> Settings -> Get changed appointments (PracticeQ, updated since yesterday)
  -> Queue bookings (new booking? start/extend 30-min timer; whose timer ran out?)
  -> Get upcoming (PracticeQ, that client, from today) -> Build PDFs
  -> Upload to client file (POST /files/{clientId}) -> List client files
  -> Record results (retry failures) -> Pick old summaries -> Delete old summary
```

Source: `n8n/appointment-summary/` (`queue.js`, `build-pdfs.js`, `finish.js`, `replace.js`
are the Code nodes; `build.mjs` writes `workflow.json`; `node --test n8n/appointment-summary/test.mjs` runs
the tests, which need `pdftotext`/`pdfinfo` from poppler).

## What counts as a booking

- **Triggers a PDF:** a new appointment created in PracticeQ, status Confirmed or
  Waiting Confirmation, starting in the future.
- **Pushes the PDF back** (only while that patient is already waiting): any change to any of
  their appointments, e.g. another booking, reschedule, cancellation.
- **Never triggers a PDF:** edits to a patient who isn't waiting (marking a visit attended,
  invoicing, notes), back-dated entries, appointments booked and cancelled before the
  workflow saw them.
- **Listed in the PDF:** that patient's Confirmed and Waiting Confirmation appointments from
  now on (the latter marked "(pending)"), with date, time, visit type, provider, location.
  If everything was cancelled during the wait, nothing is uploaded.

The file is named `Upcoming appointments YYYY-MM-DD.pdf`, and it **replaces** the patient's
previous summary: once the new PDF has uploaded, older files named exactly
`Upcoming appointments <date>.pdf` in that patient's Files are deleted. Nothing else is ever
deleted (a renamed copy such as `Upcoming appointments 2026-09-20 (signed).pdf` is left
alone). If the upload or the file list fails, nothing is deleted, so a patient always has at
least one summary. In test mode only the test client's `TEST - <patient> - ...` files are
replaced.

## Setup (about 10 minutes)

1. **Import.** In n8n: Workflows > Import from File > `n8n/appointment-summary/workflow.json`.
   It imports inactive.

2. **PracticeQ credential.** Create a credential of type *Header Auth*, named
   `PracticeQ API (X-Auth-Key)`: Name `X-Auth-Key`, Value = your existing PracticeQ API key.
   **Do not generate a new key in PracticeQ.** Only one key can be active, and a new one
   breaks the cockpit (Secret Manager `cockpit-intakeq-key`) and anything else using the
   current key. Copy the current value instead. Pick this credential on all five
   PracticeQ steps ("Get changed appointments", "Get upcoming", "Upload to client file",
   "List client files", "Delete old summary").

3. **Test client.** In PracticeQ, create a dummy client (e.g. "Test Patient") and note its
   client id (the number in the URL of its profile).

4. **Settings node.** Fill in:
   | Setting | Value |
   |---|---|
   | `mode` | `test` for now (see step 5) |
   | `testClientId` | the dummy client's id; in test mode every PDF is uploaded there instead |
   | `bufferMinutes` | `30` |
   | `timezone` | `America/New_York` (times in the PDF are shown in this zone) |
   | `practiceName`, `practicePhone` | as they should appear on the PDF |

5. **Test for a few days.** Activate the workflow with `mode` = `test`. Every PDF lands in the
   test client's Files, named `TEST - <patient> - Upcoming appointments ....pdf`. Compare a few
   against the real schedules. The first run after activation only sets a starting point, so
   book a test appointment **after** activating. Note: n8n keeps the queue only for runs of
   the active workflow; clicking "Test workflow" manually always behaves as a first run and
   uploads nothing.

6. **Go live.** Set `mode` = `live` and save. PDFs now go to each patient's own file.

Check once whether files uploaded through the API are visible to the patient in the client
portal on your account; that is a PracticeQ setting, not something this workflow controls.

## Operating notes

- **Load on PracticeQ:** each 5-minute check reads every appointment changed since yesterday,
  100 per call, so 1 to a few calls per check: roughly 300 to 1,000 a day depending on how busy
  the schedule is. Each PDF adds 4 calls (fetch, upload, list, delete), paced 3.5 s apart.
  Your account allows 20 a minute (no daily cap), shared with the cockpit and the existing
  workflow. This is the first automation that *writes* to PracticeQ: it uploads files and
  deletes only its own earlier summary files.
- **Failures:** a failed upload is retried after 10 minutes, 3 attempts in total. Every run
  logs one line per PDF in "Record results" (`uploaded`, `failed, will retry`,
  `failed, gave up`). If PracticeQ is down during the fetch, the run errors and the next run
  picks up. Consider setting an n8n Error Workflow so failures notify someone.
- **Downtime:** if n8n is off for more than a day, bookings made in that gap get no PDF (the
  lookback is one day), so a restart never back-fills old bookings.
- **Changing the layout:** edit `build-pdfs.js`, run `node n8n/appointment-summary/build.mjs`,
  re-import, or paste the file into the "Build PDFs" node.
- **Pausing:** deactivate the workflow. Bookings made while it is off (up to a day) are
  picked up when it is reactivated.

## Why polling every 5 minutes, not a trigger on booking

PracticeQ sends appointment events to one webhook URL only, and that slot is used by the
"IntakeQ Appointments -> GHL" workflow. Triggering on booking would mean adding a forwarding
step to that workflow, plus shared storage (an n8n Data Table) so separate trigger runs can
agree on whose 30-minute timer is the latest. A trigger would use far fewer API calls (only
the 4 per PDF, none for checking), but with a 30-minute buffer it would file the PDF at most
5 minutes sooner, and the polling load is within the account's limit.
