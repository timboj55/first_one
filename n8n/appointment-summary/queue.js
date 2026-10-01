// Code node "Queue bookings" (run once for all items).
// Input: appointments PracticeQ reports as updated since yesterday (one item each, or one
// empty item when there are none). Output: one item per client whose summary is due now.
//
// A client enters the queue when a new open appointment is booked for them. Any further
// change to that client's appointments while they wait (another booking, a reschedule, a
// cancellation) pushes the send time back, so the email goes out once the schedule has been
// quiet for `bufferMinutes`. Edits to clients who are not waiting (marking a visit attended,
// invoicing) never trigger an email.
const s = $('Settings').first().json;
const state = $getWorkflowStaticData('global');
const OPEN = ['Confirmed', 'WaitingConfirmation'];
const now = Date.now();
const bufferMs = Number(s.bufferMinutes) * 60000;
state.pending = state.pending || {};

const rows = $input.all().map((i) => i.json).filter((r) => r && r.Id);

if (state.cursor === undefined) {
  // First run: watch from now on, never email for changes made before the switch-on.
  state.cursor = rows.reduce((m, r) => Math.max(m, Number(r.LastModified) || 0), now);
  return [];
}

const since = state.cursor;
let cursor = since;
for (const r of rows) {
  const modified = Number(r.LastModified) || 0;
  if (modified <= since) continue;
  cursor = Math.max(cursor, modified);

  const key = String(r.ClientId);
  const waiting = state.pending[key];
  const newBooking = Number(r.DateCreated) > since && OPEN.includes(r.Status) && Number(r.StartDate) > now;
  if (!waiting && !newBooking) continue;

  state.pending[key] = {
    clientId: r.ClientId,
    email: r.ClientEmail || (waiting && waiting.email) || '',
    name: r.ClientName || (waiting && waiting.name) || '',
    dueAt: Math.max(waiting ? waiting.dueAt : 0, modified + bufferMs),
    attempts: waiting ? waiting.attempts : 0,
  };
}
state.cursor = cursor;

const due = [];
for (const [key, p] of Object.entries(state.pending)) {
  if (p.dueAt <= now) {
    due.push(p);
    delete state.pending[key];
  }
}
return due.map((p) => ({ json: p }));
