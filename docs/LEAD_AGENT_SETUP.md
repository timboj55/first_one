# Lead follow-up agent (after hours + busy hours): setup and operations

`lead_agent/` texts and calls new GoHighLevel (GHL) leads when the team can't, and books a
**Cost & Availability call** on the GHL calendar. Text runs on Claude through the GHL
Conversations API. Voice runs on Retell AI (streaming speech, ElevenLabs voice, barge-in,
backchannels) with the booking brain still in this service.

## How it behaves

```
GHL workflow "new lead" ──webhook──▶ lead_agent ──▶ decides: engage now?
                                                    ├─ after hours / holiday ........ yes, now
                                                    ├─ busy mode on .................. yes, now
                                                    └─ office hours .................. wait 5 min; if nobody on
                                                                                       the team has touched the
                                                                                       lead, engage
cadence (agent_config.json)   T+0  SMS opener  → T+4m call → T+90m SMS → next day call → SMS → final SMS
                              every touch re-checks: stop tag, DND, already booked, human replied
lead texts back ──────────▶ Claude replies, offers real calendar slots, books, confirms
lead goes quiet ──────────▶ nudge at +2h, +1d, +3d
voice call ───────────────▶ Retell agent offers pre-fetched slots, calls back into
                            /voice/tools/* to check/book; transcript + summary → GHL note
stop conditions             booked (by us or anyone), STOP/opt-out, not interested, wrong number,
                            existing patient, human messaged the lead, `ai-agent-stop` tag, DND
quiet hours                 nothing sent 8:30pm–8am lead-local; calls only 9am–7:30pm
```

Everything the agent does lands in GHL: tags (`ai-agent-*`), notes (bookings, handoffs, call
transcripts), the appointment itself, and the SMS thread in Conversations.

## 1. Prerequisites

| Item | Where |
|---|---|
| GHL Private Integration token | Sub-account Settings > Private Integrations > create. Scopes: `contacts.readonly`, `contacts.write`, `conversations.readonly`, `conversations/message.write`, `calendars.readonly`, `calendars/events.write`, `calendars/events.readonly`. |
| GHL location id | `GZecKV1IvZgcZdeVItxt` (the sub-account id used by the existing n8n booking workflow) |
| GHL calendar id | The inquiry-call calendar. The n8n "HTML -> GHL Calendar Booking" workflow uses `cEAl8rVZptX0GMvhT4gH` for the Cost & Availability calendar and `eXLp1htlxqRKxsGxDxcO` for the $97 consult. |
| Anthropic API key | console.anthropic.com. The SMS brain uses `claude-opus-5-5` (configurable). |
| Retell account | retellai.com: API key, a phone number (buy or import your GHL/Twilio number), and a voice. |
| A public HTTPS URL | For GHL and Retell webhooks. Any host works: a small VM with Caddy, Fly.io, Railway, or a Cloudflare Tunnel to the n8n host. |

## 2. Deploy the service

```bash
cp .env.example .env    # fill the LEAD_AGENT section
docker build -t lead-agent .
docker run -d --name lead-agent --env-file .env -p 8080:8080 -v lead_agent_data:/data lead-agent
# or without Docker:
pip install -r requirements.txt && python3 -m lead_agent serve
```

Put HTTPS in front (Caddy: `reverse_proxy localhost:8080`). Then:

```bash
python3 -m lead_agent check      # validates env + pulls free slots from the calendar
curl https://YOUR_HOST/healthz
```

Env vars (all in `.env.example`): `ANTHROPIC_API_KEY`, `GHL_TOKEN`, `GHL_LOCATION_ID`,
`GHL_CALENDAR_ID`, `GHL_SMS_FROM_NUMBER` (optional), `GHL_WEBHOOK_SECRET`, `ADMIN_SECRET`,
`RETELL_API_KEY`, `RETELL_AGENT_ID`, `RETELL_FROM_NUMBER`, `PUBLIC_BASE_URL`, `LEAD_AGENT_DB`.
Generate secrets with `openssl rand -hex 24`.

Set `LEAD_AGENT_DRY_RUN=1` to run everything except the writes (no SMS, no calls, no
bookings): the decisions and the drafted texts show up in the logs and in `status`.

## 3. Wire up GHL (three workflows)

All three use the workflow action **Webhook** (Custom Webhook), method POST, URL below, and
add **Custom Data** fields so the payload is unambiguous regardless of trigger defaults.

### 3a. New lead → `POST https://YOUR_HOST/webhooks/ghl/<GHL_WEBHOOK_SECRET>/new-lead`

Trigger: whatever creates leads today (Form Submitted, Survey Submitted, Facebook Lead Form,
Contact Created with source filters, Chat Widget, missed call). Custom data:

| key | value |
|---|---|
| `contact_id` | `{{contact.id}}` |
| `service_interest` | the form field for "what are you reaching out about" (or a static value per funnel) |
| `message_body` | the free-text message field, if any |

Standard contact fields (first name, phone, email, tags, source, timezone) come through
automatically. Leads with no phone are skipped.

Optional filters before the webhook: skip contacts tagged `existing-patient`, or only run for
specific sources. The service also skips anyone with a DND on SMS, the `ai-agent-stop` tag, or
an existing appointment on the inquiry calendar.

### 3b. Customer Replied (SMS) → `POST .../inbound-message`

Trigger: **Customer Replied**, reply channel = SMS. Custom data:

| key | value |
|---|---|
| `contact_id` | `{{contact.id}}` |
| `message_body` | `{{message.body}}` |
| `message_type` | `SMS` |
| `message_id` | `{{message.id}}` (if available; used to de-duplicate) |

Only contacts the agent is already working with get a reply; everyone else is ignored (set
`"engage_on_unknown_inbound": true` in `agent_config.json` to change that).

### 3c. Appointment booked → `POST .../appointment-booked`

Trigger: **Appointment** (status booked/confirmed) on the inquiry calendar. Custom data:
`contact_id` = `{{contact.id}}`, `appointment_id` = `{{appointment.id}}`. This stops outreach
when the lead books through the widget or a team member books them.

### 3d. Team controls (no workflow needed)

- **Stop the agent on one lead:** add tag `ai-agent-stop`. The next touch is skipped.
- **Take over a thread:** just text the lead from GHL. The agent notices an outbound message it
  did not send, tags `ai-agent-paused-human`, adds a note and goes quiet.
- **Busy mode (whole office):** `python3 -m lead_agent busy on|off`, or
  `curl -X POST https://YOUR_HOST/admin/<ADMIN_SECRET>/busy -d '{"on":true}'`. When on, the
  agent engages new leads immediately even during office hours. Tip: a GHL workflow with a
  manual trigger and a webhook to that URL gives the front desk a one-click button.

## 4. Wire up Retell (voice)

1. In Retell: create an API key; buy a number (or import your existing one via SIP/Twilio) and
   note it as `RETELL_FROM_NUMBER` in E.164.
2. Pick a voice in Retell's voice library and put its id in `agent_config.json` → `voice.voice_id`
   (`11labs-…` ids are ElevenLabs; listen to a few and pick one that matches the front desk).
3. `PUBLIC_BASE_URL` and `RETELL_API_KEY` set → run:

   ```bash
   python3 -m lead_agent setup-voice --print   # inspect the generated LLM + agent config
   python3 -m lead_agent setup-voice           # creates (or updates) them in Retell
   ```

   It prints `agent_id`; put it in `.env` as `RETELL_AGENT_ID`. Re-run after editing prompts
   or voice settings in `agent_config.json`; ids are remembered in `.lead_agent_voice.json`.
4. In Retell, bind the phone number's **outbound agent** to that agent id (the service also
   passes `override_agent_id` on every call).
5. Test from the Retell dashboard with dynamic variables `lead_first_name`, `service_interest`,
   `offered_slots_spoken`, then run a real outbound test to your own phone by simulating a
   lead (section 6).

What makes it sound human (all in `agent_config.json` → `voice`): ElevenLabs Flash v2.5 voice,
backchannels ("mm-hmm", "gotcha") at 0.7 frequency, faint call-center room tone, high
responsiveness with dynamic pacing, interruption sensitivity 0.8 so the lead can talk over it,
short reminder prompts on silence, a scripted voicemail drop, and a prompt written for speech
(contractions, one idea at a time, times said the way people say them). The Retell LLM runs
`claude-5-sonnet` for low latency; the booking tools call back into this service so both
channels book the same way.

## 5. Compliance (read before going live)

- **Consent.** Automated/AI voice calls and marketing texts to mobile numbers require prior
  express written consent (TCPA; the FCC treats AI-generated voices as "artificial"). Put a
  clear consent line on every lead form ("By submitting, you agree to receive calls and texts,
  including automated and AI-assisted messages, from Movement Solutions at the number
  provided. Msg & data rates may apply. Reply STOP to opt out."). If some funnels lack that
  line, tag consented leads and set `tags.consent` in `agent_config.json`; the agent then only
  contacts tagged leads.
- **Disclosure.** The voice agent introduces itself as the practice's virtual assistant and
  both channels answer honestly if asked whether they are an AI. Keep that on: several states
  require bot disclosure, and it costs nothing in bookings. Adjust wording via `voice.disclosure_line`.
- **Quiet hours.** No texts 8:30pm–8am and no calls outside 9am–7:30pm, in the lead's
  timezone when GHL has it. Tighten in `hours` if you serve other states.
- **Opt-out.** STOP/UNSUBSCRIBE marks the contact DND for SMS and calls, tags it, and the
  agent stops. GHL's carrier-level STOP handling still applies.
- **Recording.** Retell records calls by default. South Carolina is one-party consent, but
  leads can be anywhere; either add a recording disclosure to the opening line or disable
  recording on the Retell agent. Set `voice.opt_out_sensitive_data_storage` to `true` to keep
  transcripts/recordings out of Retell's storage (the transcript still reaches GHL via webhook).
- **PHI.** Leads describe symptoms. Retell offers a BAA on its enterprise tier; Anthropic
  offers a BAA and zero-data-retention on request (note that `claude-opus-5-5` supports ZDR;
  the Fable tier does not). Keep this in mind when choosing vendors and tiers.

## 6. Test it before real leads

```bash
# 1. Pure logic, no network:
python3 -m unittest tests.test_lead_agent -v

# 2. Talk to the SMS brain locally (real Claude, fake GHL calendar, nothing sent):
ANTHROPIC_API_KEY=... python3 -m lead_agent simulate --name "Sam Rivera" --interest "knee pain after running"

# 3. End to end in dry run against your real GHL/Retell config (reads only):
LEAD_AGENT_DRY_RUN=1 python3 -m lead_agent serve
curl -X POST https://YOUR_HOST/admin/<ADMIN_SECRET>/simulate/new-lead \
     -H 'Content-Type: application/json' \
     -d '{"contact_id":"<a real test contact id>","first_name":"Test","phone":"+1YOURPHONE","customData":{"service_interest":"back pain"}}'
python3 -m lead_agent status <contact id>      # timeline: decisions, drafted texts, deferrals

# 4. Live, with your own phone as the lead: same as 3 without DRY_RUN, after hours or with busy mode on.
```

## 7. Tuning

Everything lives in `agent_config.json`:

- `practice.*` tone, FAQ answers, things never to say, what the inquiry call is.
- `hours.*` office hours, holidays, quiet hours, call window.
- `busy_mode.auto_after_minutes_unanswered` how long the team gets during office hours.
- `cadence.initial` the touch sequence and delays; `cadence.after_reply_silence` the nudges;
  `max_sms`, `max_calls` hard caps per lead.
- `models.sms` / `models.sms_effort` the Claude model and effort for texting.
- `voice.*` voice id, model, backchannel, ambient sound, pacing, voicemail text, transfer number.

Restart the service (and re-run `setup-voice` for voice changes) after edits.

## 8. Operating notes

- State is a SQLite file (`LEAD_AGENT_DB`). Back it up with the volume; it holds transcripts.
- `python3 -m lead_agent status` lists conversations; with a contact id it shows the full
  timeline (every decision, deferral, text, tool call and call result).
- Transient failures (rate limits, GHL 5xx) retry with backoff; permanent failures are logged
  as `job_failed` events and never block other leads.
- The agent treats any outbound SMS it did not send as a human takeover. If other GHL
  workflows text new leads too, either exclude contacts tagged `ai-agent-active` from those
  workflows or accept that such a text pauses the agent.
- GHL API limits (100 req/10s burst, 200k/day per location) are far above what this uses.

## Not yet verified against live accounts

The GHL endpoints and payload shapes were checked against the community typings and your
existing n8n workflows; the Retell request/response shapes against Retell's published Python
SDK. Neither has been exercised here with real credentials (the container has none). First
live checks: run `python3 -m lead_agent check` (calendar slots), send one dry-run lead, then
one real text to your own number, then one real call.
