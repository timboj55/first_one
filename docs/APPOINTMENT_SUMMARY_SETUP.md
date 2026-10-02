# Booking summary PDF (n8n)

When a patient is booked in PracticeQ, a one-page PDF listing **all** their upcoming
appointments is uploaded to their PracticeQ client file (Files tab), **30 minutes after the
last change** to their schedule, and it **replaces** their previous summary PDF. Booking
several visits in a row, or fixing a mistake (reschedule, cancel, rebook) inside those 30
minutes, restarts the timer, so one correct PDF is filed. The list is read fresh from
PracticeQ at upload time.

It runs on PracticeQ's own appointment events, not by checking PracticeQ on a timer, and it
only files PDFs during **business hours plus one hour** after closing.

## How it works

```
"IntakeQ Appointments -> GHL" (existing)
   PracticeQ webhook ──> [new] Forward to booking summary ──┐
                     └─> (everything it already does)         │
                                                              v
"PracticeQ booking summary PDF" (new)
   Appointment event -> Classify event -> Add to queue          (any time, no PracticeQ calls)

   Every 5 minutes -> Settings -> Business hours? -> Read queue -> Due patients
     -> Remove from queue -> Keep due -> Get upcoming -> Build PDFs -> Upload to client file
     -> List client files -> Record results -> Pick old summaries -> Delete old summary
                                           └-> Retries -> Re-queue failed
```

- **Events are queued at any hour.** Every appointment event (created, confirmed,
  rescheduled, cancelled, declined, missed, deleted) adds a row to an n8n data table,
  `booking_summary_queue`. This costs no PracticeQ calls.
- **The sweeper runs every 5 minutes, but only in the business window.** Outside it, the run
  stops at "Business hours?" without reading anything. Inside it, it reads the queue (an
  n8n-internal table, not PracticeQ) and picks patients whose last event is at least 30
  minutes old.
- **Only patients with a new booking get a PDF.** A patient's events produce a PDF only if
  one of them is a new appointment (Confirmed or Waiting Confirmation, starting in the future).
  Events for patients without a new booking, such as a cancellation on its own, are dropped.
- **PracticeQ is only called when a PDF is made**, 4 calls per PDF (read schedule, upload,
  list files, delete the old summary), paced 3.5 s apart. At most 10 PDFs per run.
- **Business window** (from `agent_config.json`, the same table the GHL lead agent uses):

  | Day | Business hours | PDFs filed until |
  |---|---|---|
  | Mon–Thu | 8:00–17:00 | 18:00 |
  | Fri | 8:00–16:00 | 17:00 |
  | Sat, Sun | closed | none |
  | Holidays (2026-11-26, 2026-12-25, 2027-01-01) | closed | none |

  Bookings made outside the window are kept and filed at the next opening (e.g. a Friday
  9pm online booking is filed Monday at 8:00). The Settings node holds these hours; edit
  `businessHours`, `afterCloseMinutes` or `holidays` there.

**The PDF:** that patient's Confirmed and Waiting Confirmation appointments from now on (the
latter marked "(pending confirmation)"), with date and time only (no provider, visit type or location), named
`Upcoming appointments YYYY-MM-DD.pdf`. If everything was cancelled during the wait, nothing
is uploaded.

**Replacing:** once the new PDF has uploaded, older files named exactly
`Upcoming appointments <date>.pdf` in that patient's Files are deleted. Nothing else is ever
deleted (a renamed copy such as `Upcoming appointments 2026-09-20 (signed).pdf` is left
alone). If the upload or the file list fails, nothing is deleted, so a patient always has at
least one summary. In test mode only the test client's `TEST - <patient> - ...` files are
replaced.

Source: `n8n/appointment-summary/`. The `.js` files are the Code nodes, `build.mjs` writes
`workflow.json` and `forward-node.json`, and `node --test n8n/appointment-summary/test.mjs`
runs the tests (they need `pdftotext`/`pdfinfo` from poppler).

## Setup (about 20 minutes)

1. **Data table.** In n8n: Overview > Data tables > Create, named exactly
   `booking_summary_queue`, with these columns:

   | Column | Type |
   |---|---|
   | `clientId` | String |
   | `clientName` | String |
   | `clientEmail` | String |
   | `eventAt` | Number |
   | `isBooking` | Boolean |
   | `attempts` | Number |

2. **Import the new workflow.** Workflows > Import from File >
   `n8n/appointment-summary/workflow.json`. It imports inactive. Open the four data-table
   steps ("Add to queue", "Read queue", "Remove from queue", "Re-queue failed") and confirm
   each shows `booking_summary_queue`; if one is blank, pick the table from the list.

3. **Webhook key.** Create a credential of type *Header Auth*, named
   `Booking summary webhook key`: Name `X-Booking-Summary-Key`, Value = a long random string
   (e.g. from a password generator). Pick it on "Appointment event". It stops anyone else
   from posting to this workflow.

4. **PracticeQ credential.** Create a credential of type *Header Auth*, named
   `PracticeQ API (X-Auth-Key)`: Name `X-Auth-Key`, Value = your existing PracticeQ API key.
   **Do not generate a new key in PracticeQ.** Only one key can be active, and a new one
   breaks the cockpit (Secret Manager `cockpit-intakeq-key`) and anything else using the
   current key. Copy the current value instead. Pick it on the four PracticeQ steps: "Get
   upcoming", "Upload to client file", "List client files" and "Delete old summary".

5. **Test client.** In PracticeQ, create a dummy client (e.g. "Test Patient") and note its
   client id (the number in the URL of its profile).

6. **Settings node.** Set `testClientId` to the dummy client's id and `practicePhone` to the
   number to show on the PDF. Leave `mode` = `test`. The other settings are already filled
   in (30-minute buffer, `America/New_York`, the hours above).

7. **Activate the new workflow**, then open "Appointment event" and copy its **Production
   URL** (ends in `/webhook/booking-summary`).

8. **Forward events from the existing workflow.** This is the one change to
   "IntakeQ Appointments -> GHL":
   1. Open it, open `n8n/appointment-summary/forward-node.json` in a text editor, copy all of
      it, and paste into the canvas (Ctrl/Cmd+V). A node "Forward to booking summary" appears.
   2. Drag a connection from the workflow's **PracticeQ webhook node** (its first node) to the
      new node, as an extra branch. Leave the existing connections as they are.
   3. In the new node, replace the URL with the Production URL from step 7 and pick the
      `Booking summary webhook key` credential.
   4. Save. The node is set to continue on error, so if the summary workflow is ever off, the
      existing GHL automation carries on unaffected.

9. **Test for a few days.** Book a test appointment for any patient. Within about 35 minutes
   (during business hours) a PDF named `TEST - <patient> - Upcoming appointments ....pdf`
   appears in the test client's Files. Compare a few against the real schedules.

10. **Go live.** Set `mode` = `live` and save. PDFs now go to each patient's own file.

Check once whether files uploaded through the API are visible to the patient in the client
portal on your account; that is a PracticeQ setting, not something this workflow controls.

## Operating notes

- **Load on PracticeQ:** none while nothing is booked; 4 calls per PDF. This is the first
  automation that *writes* to PracticeQ: it uploads files and deletes only its own earlier
  summary files.
- **Failures:** a failed upload is put back in the queue and retried about 10 minutes later,
  3 attempts in total (only within business hours). "Record results" logs one line per PDF
  (`uploaded` or `failed`). If PracticeQ is down when the schedule is read, that run errors
  and those patients are not retried, so consider setting an n8n Error Workflow so failures
  notify someone.
- **If the new workflow is off**, events forwarded meanwhile are lost (the forward step
  just carries on), so those bookings get no PDF. Turn it back on and new bookings work
  again.
- **The queue table** normally holds only patients waiting for their PDF, so it stays small.
  Deleting all rows is safe; it only cancels the PDFs not filed yet.
- **Changing the layout:** edit `build-pdfs.js`, run `node n8n/appointment-summary/build.mjs`,
  then paste the file into the "Build PDFs" node (or re-import).
- **Email version:** an earlier version emailed the list through GHL instead; it is in git
  history at commit `37d6772`.

## Live setup (done 2026-10-02)

- Data table `booking_summary_queue` created (id `kBtcS2vdYqN6CKt1`).
- Workflow "PracticeQ booking summary PDF" imported (id `QTVvGJf02pD6Rb4Z`), **active in test mode**:
  `testClientId` 2425, `practicePhone` (864) 558-7346, `bufferMinutes` 5 (changed from 30 at the owner's request; with the 5-minute sweep a summary lands 5-10 minutes after the last change).
- Differences from the steps above: the four PracticeQ steps reuse the existing n8n credential
  "IQ Authorization" (the one "IntakeQ Appointments -> GHL" uses), and "Appointment event" uses a
  secret random webhook path with no auth, like the existing PracticeQ webhook. So no
  "Booking summary webhook key" or new PracticeQ credential exists.
- "IntakeQ Appointments -> GHL" (id `udqmSYwWyreYJ6IO`) gained one node, "Forward to booking
  summary", wired from its Webhook node as a second branch, continue-on-error. Its other 10 nodes
  and settings are unchanged. To undo: delete that node in the editor.
- Still to do: test, then set `mode` = `live`; remove the write scopes from the
  "Claude cloud - setup" n8n API key.
