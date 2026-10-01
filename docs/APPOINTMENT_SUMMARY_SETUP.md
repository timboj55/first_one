# Booking summary email (n8n)

When a patient is booked in PracticeQ, they get one email listing **all** their upcoming
appointments, sent **30 minutes after the last change** to their schedule. Booking several
visits in a row, or fixing a mistake (reschedule, cancel, rebook) inside those 30 minutes,
restarts the timer, so the patient gets one correct email. The list is read fresh from
PracticeQ at send time. The email goes out through GHL, so it shows in the contact's
conversation and respects GHL's email DND.

It is a **separate n8n workflow**. The existing "IntakeQ Appointments -> GHL" workflow and the
PracticeQ webhook are not touched.

```
Every 5 minutes -> Settings -> Get changed appointments (PracticeQ, updated since yesterday)
  -> Queue bookings (new booking? start/extend 30-min timer; whose timer ran out?)
  -> Get upcoming (PracticeQ, that client, from today) -> Build emails
  -> Find GHL contact (upsert by email) -> Send email (GHL) -> Record results (retry failures)
```

Source: `n8n/appointment-summary/` (`queue.js`, `build-emails.js`, `finish.js` are the Code
nodes; `build.mjs` writes `workflow.json`; `node --test n8n/appointment-summary/test.mjs` runs
the tests).

## What counts as a booking

- **Triggers an email:** a new appointment created in PracticeQ, status Confirmed or
  Waiting Confirmation, starting in the future.
- **Pushes the email back** (only while that patient is already waiting): any change to any
  of their appointments, e.g. another booking, reschedule, cancellation.
- **Never triggers an email:** edits to a patient who isn't waiting (marking a visit
  attended, invoicing, notes), back-dated entries, appointments booked and cancelled before
  the workflow saw them.
- **Listed in the email:** that patient's Confirmed and Waiting Confirmation appointments from
  now on (the latter marked "awaiting confirmation"). If everything was cancelled during the
  wait, nothing is sent.

## Setup (about 15 minutes)

1. **Import.** In n8n: Workflows > Import from File > `n8n/appointment-summary/workflow.json`.
   It imports inactive.

2. **PracticeQ credential.** Create a credential of type *Header Auth*, named
   `PracticeQ API (X-Auth-Key)`: Name `X-Auth-Key`, Value = your existing PracticeQ API key.
   **Do not generate a new key in PracticeQ.** Only one key can be active, and a new one
   breaks the cockpit (Secret Manager `cockpit-intakeq-key`) and anything else using the
   current key. Copy the current value instead. Pick this credential on "Get changed
   appointments" and "Get upcoming".

3. **GHL credential.** In GHL: Settings > Private Integrations > create one with scopes
   **View/Edit Contacts** and **View/Edit Conversation Messages**. In n8n, create a
   *Header Auth* credential named `GHL Private Integration (Bearer)`: Name `Authorization`,
   Value `Bearer <token>`. Pick it on "Find GHL contact" and "Send email".

4. **Settings node.** Fill in:
   | Setting | Value |
   |---|---|
   | `mode` | `test` for now (see step 5) |
   | `testEmail` | your own inbox; in test mode every summary goes here instead of to the patient |
   | `bufferMinutes` | `30` |
   | `timezone` | `America/New_York` (times in the email are shown in this zone) |
   | `practiceName`, `practicePhone` | as they should appear in the email |
   | `ghlLocationId` | GHL sub-account id (Settings > Business Profile, or the URL after `/location/`) |

5. **Test for a few days.** Activate the workflow with `mode` = `test`. Every summary lands in
   `testEmail`, subject `[TEST for <patient> <email>] ...`. Compare a few against PracticeQ. The
   first run after activation only sets a starting point, so book a test appointment
   **after** activating. Note: n8n keeps the queue only for runs of the active workflow;
   clicking "Test workflow" manually always behaves as a first run and sends nothing.

6. **Go live.** Set `mode` = `live` and save. Emails now go to the patient.

## Operating notes

- **Load on PracticeQ:** about 1 call every 5 minutes, plus 1 per summary, paced 3.5 s
  apart. Your account allows 20 a minute, shared with the cockpit and the existing workflow.
- **Failures:** a failed GHL send is retried after 10 minutes, 3 attempts in total. Every run
  logs one line per email in "Record results" (`sent`, `failed, will retry`,
  `failed, gave up`). If PracticeQ itself is down the run errors and the next run picks up.
  Consider setting an n8n Error Workflow so failures notify someone.
- **Downtime:** if n8n is off for more than a day, bookings made in that gap don't get a
  summary (the lookback is one day), so a restart never mass-emails old bookings.
- **Contacts:** the GHL step looks up the patient by email and creates a contact if none
  exists. A patient with no email in PracticeQ gets no summary.
- **Privacy:** the email contains visit dates, visit type, provider and location. It's the
  same category of information as your existing reminders, so it should go through the same
  HIPAA-covered GHL setup (BAA) you use for those.
- **Changing the email:** edit `build-emails.js`, run `node n8n/appointment-summary/build.mjs`,
  re-import, or paste the file into the "Build emails" node.
- **Pausing:** deactivate the workflow. Bookings made while it is off (up to a day) are
  picked up when it is reactivated.
