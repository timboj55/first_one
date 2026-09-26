# GoHighLevel task -> IntakeQ task: feasibility (checked 2026-09-26)

**Short answer:** the GHL half is straightforward; the IntakeQ half is blocked because
**IntakeQ's public API has no way to create a task.** Tasks can only be created from the
PracticeQ UI, from form rules, or from Process Template automations. Until IntakeQ adds a
Tasks endpoint, a one-to-one "task here creates task there" sync cannot be built on
supported interfaces. Workarounds exist, ranked below.

## Evidence

- The API category on the support site lists nine articles (Questionnaire, Client,
  Appointments, Partner, Notes, Invoice, Rate Limits, Claims, Files). None covers tasks.
- Live probe: `GET https://intakeq.com/api/v1/tasks` (and `/task`, `/todos`) returns
  **404 "No HTTP resource was found that matches the request URI"**, whereas real endpoints
  such as `/practitioners` return 401 without a key. The route does not exist, so this is not
  an auth problem.
- Notes API is read-only (four GET methods). Client API can create/update clients, custom
  fields, tags and `PractitionerId` but has no task fields.
- Zapier integration offers two actions only: Send Form and Save Client. No task action.
- Task articles (Enable Task Management, Create a Task, Manage Tasks, Task Automation
  (Processes), Assign Tasks via Form Rules): tasks carry description, assignee, priority,
  due date/time, notes and an optional client link. Process Templates create tasks on
  events such as **Appointment created**, Appointment missed, Recurring payment failed, and
  form-rule matches; the task text in a template is fixed, the assignee can be "the
  practitioner associated with the triggering event" and the client link comes from the
  triggering object.

## GHL side (not the blocker)

- Workflow trigger **Task Added** (Contact category) followed by a **Webhook** action posts
  task and contact fields to any URL. Alternative: a Marketplace app subscribed to the
  `TaskCreate` webhook event, then `GET /contacts/{id}` and `GET /users/{id}` with a
  private-integration token to resolve the client and the assigned physical therapist.
- GHL tasks always belong to a contact and carry `assignedTo` (user id), title, body and
  due date, so "PT" and "client" are both available on every event.
- Matching: GHL assigned user email -> IntakeQ practitioner email (`GET /practitioners`);
  GHL contact email -> IntakeQ client (`GET /clients?search=`), with a fallback on name and a
  stored `ExternalClientId` on the IntakeQ client once matched.
- GHL docs hosts are blocked from this session's network policy, so trigger and payload
  field names above come from product knowledge, not a fresh fetch. Confirm the Task Added
  trigger's available merge fields in the workflow builder before relying on them.

## Options for the IntakeQ side, best first

1. **Ask IntakeQ support for a Tasks API** (create task with description, assignee,
   client, due date, priority). They have extended the API on request before (Claims API,
   cancellation fields, Resend Intake). Zero-risk, but on their timeline. Worth sending
   today regardless of what else is chosen.
2. **Reverse the direction: make GHL the task system of record.** GHL's API fully supports
   task creation (`POST /contacts/{contactId}/tasks`), so IntakeQ events (appointment
   created/missed, form submitted, invoice unpaid, all available as IntakeQ webhooks) can
   create GHL tasks for the PT and client. Fully supported both ends, no workaround.
3. **Surface the GHL task on the IntakeQ client profile without a task object.** On
   Task Added, write the task into a client custom field (for example "Open GHL tasks") via
   `POST /clients` and add a tag such as `ghl-task-open`; remove/clear on Task Completed.
   PracticeQ shows tags and custom fields on the profile and tags can drive its own
   automations. Also email the PT. Documented, reversible, no fake records. Not a task,
   so it does not appear in the task list or reminders.
4. **Trigger a Process Template through a documented API event.** Create a zero-price
   appointment on a dedicated "Internal task" service for that PT and client with
   `SendClientEmailNotification: false`, and let a Process Template with trigger
   "Appointment created" (filtered to that service) create the task; the task is assigned
   to the appointment's practitioner and linked to the client. Then cancel the appointment.
   Drawbacks: the task text is fixed in the template, so the GHL title/body cannot flow
   into the task; a canceled placeholder appointment remains on the client record and in
   reports; it burns two of the tenant's 20 requests/minute per task.
   Variant ruled out: a placeholder **note** instead of an appointment. Process Templates
   do accept a note-based trigger (the automation form's third condition can be Notes), but
   the Notes API is read-only (query summary, PDF, full note, plus the outbound Note Locked
   webhook), so a note cannot be created, locked or deleted through the API. Appointments
   are the only API-writable object that fires a Process trigger. Untested edge: the
   Questionnaire API can update office-use questions on an existing intake; if form rules
   re-evaluate on that update, a hidden office-use question could fire a Process. The docs
   do not say rules run on API updates.
5. **Browser automation** (Playwright logged in as a staff user filling the New Task
   form). Carries every field, but is cookie-session based, breaks on UI changes and MFA,
   and is not something to run a PHI-handling production pipeline on. Fallback only.

## If built: recommended shape

A small receiver (n8n workflow, or a stdlib Python handler next to
`intakeq_packages/webhook.py`) that accepts the GHL webhook, resolves practitioner and
client, then calls a pluggable `task_sink`. Start with sink 3 today, swap in sink 1 when
IntakeQ ships an endpoint. The GHL trigger, the matching code and the audit log stay the
same across sinks. Option 2 is the better long-term architecture if the practice is
willing to work tasks in GHL rather than IntakeQ.
