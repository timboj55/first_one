// Code node "Due patients" (run once for all items). Sweeper branch.
// Input: every row in the "booking_summary_queue" data table. Output: one item per patient
// whose last appointment event is at least `bufferMinutes` old. `upTo` is that last event
// time; rows up to it are removed from the queue, later rows stay for the next round.
// Patients whose events include no new booking come out with `discard: true` (removed from
// the queue, no PDF). At most MAX_PER_RUN PDFs per run, so a run finishes well inside 5 minutes.
const s = $('Settings').first().json;
const MAX_PER_RUN = 10;
const now = Date.now();
const bufferMs = Number(s.bufferMinutes) * 60000;

const groups = {};
for (const { json: r } of $input.all()) {
  if (!r || !r.clientId) continue;
  (groups[String(r.clientId)] = groups[String(r.clientId)] || []).push(r);
}

const due = [];
const discard = [];
for (const [clientId, rows] of Object.entries(groups)) {
  rows.sort((a, b) => Number(a.eventAt) - Number(b.eventAt));
  const upTo = Number(rows[rows.length - 1].eventAt);
  if (upTo + bufferMs > now) continue; // still inside the buffer
  const latest = (field) => [...rows].reverse().map((r) => r[field]).find((v) => v) || '';
  const item = {
    clientId,
    name: latest('clientName'),
    email: latest('clientEmail'),
    attempts: Math.max(...rows.map((r) => Number(r.attempts) || 0)),
    upTo,
    discard: !rows.some((r) => r.isBooking === true || r.isBooking === 'true'),
  };
  (item.discard ? discard : due).push(item);
}
due.sort((a, b) => a.upTo - b.upTo);
return [...due.slice(0, MAX_PER_RUN), ...discard].map((json) => ({ json }));
