# Cowork task: GHL "new lead → call alert" workflow (browser steps)

Paste everything below this line into a Cowork session in the Claude desktop app.

---

You are building one automation in my GoHighLevel (GHL) account in my browser. When a new lead is
added to our lead pipeline, GHL must call our team through our GHL number (864) 558-7346 and play
the whisper "We have a new lead. Please double call them immediately."

Rules: never type, paste or read out any password, API key or token. Do not edit, pause or delete
any existing workflow, pipeline, phone number or user. Only create the one new workflow described
here. If a step needs a decision I have not made, or the screen doesn't match these steps, stop and
ask me.

## 1. Check the phone setup (read only)
- Settings > Phone Numbers: find (864) 558-7346. Record its forwarding number (the phone that
  rings) and whether call recording is on. Do not change anything.
- Settings > My Staff: for each user, record whether a phone number is set under
  Call & Voicemail settings. Do not change anything.
- (864) 558-7346 is our LC Phone number. It places the call, but the call has to ring a real phone
  (the forwarding number above or a user's phone). If neither is set, stop and ask me which phone
  should ring before building anything.

## 2. Pick the pipeline
- Opportunities > Pipelines: list the pipeline names and each one's first stage.
- If exactly one pipeline is clearly for new leads (for example "Leads" or "New Patient Leads"),
  use it. Otherwise stop and ask me which one to use.

## 3. Build the workflow
Automation > Workflows > Create Workflow > Start from Scratch. Name it
`New Lead → Call Alert (864-558-7346)`.

Triggers (add both):
1. **Opportunity Created**, filter: In pipeline = the pipeline from step 2.
2. **Pipeline Stage Changed**, filters: In pipeline = the pipeline from step 2, and
   Pipeline stage = its first stage. (This catches leads moved into the pipeline.)

Action: **Call** (Communication section; older accounts call it "Call Connect").
- Whisper message: `We have a new lead. Please double call them immediately.`
- From number / outbound number (if the field exists): (864) 558-7346.
- Timeout: 30 seconds.
- Disable voicemail detection: leave OFF (so voicemail doesn't count as answered).
- Record call: match what step 1 found for the number.

Settings (gear icon in the workflow): turn **Allow re-entry** ON, so a contact who comes back as a
new opportunity later triggers the alert again.

Save. Do NOT publish yet.

## 4. Stop and confirm with me
Show me a summary of the triggers, their filters and the Call action settings. Publish only after
I say yes.

## 5. Test (only after I approve and it is published)
Ask me for a phone number to use as the test lead. Create a contact named `TEST Lead Alert` with
that phone, then add an opportunity for it in the pipeline's first stage. Tell me to watch for the
call. After I confirm it worked (or didn't), check the workflow's Execution Logs and record what
happened. Then delete the test opportunity and the `TEST Lead Alert` contact.

## 6. Report back
- Forwarding number on (864) 558-7346, and which users have phones set
- Pipeline and first stage used
- Workflow name, whether it's published, and both triggers with their filters
- Call action settings as saved (whisper, from number, timeout, voicemail detection, recording)
- Test result from the Execution Logs
