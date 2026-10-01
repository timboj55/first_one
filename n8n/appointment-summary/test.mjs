// Runs the three Code nodes outside n8n with a fake $, $input, static data and clock.
//   node n8n/appointment-summary/test.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const MIN = 60000;
const T0 = Date.UTC(2026, 9, 1, 14, 0); // 1 Oct 2026, 10:00 ET
const DAY = 24 * 60 * MIN;

const SETTINGS = {
  mode: 'test', testEmail: 'front-desk@example.com', bufferMinutes: 30, timezone: 'America/New_York',
  practiceName: 'Movement Solutions', practicePhone: '555-0100', ghlLocationId: 'loc',
};

function node(file) {
  const body = readFileSync(join(here, file), 'utf8');
  const fn = new Function('$input', '$', '$getWorkflowStaticData', 'Date', body);
  return ({ input = [], nodes = {}, state, now, settings = SETTINGS }) => {
    class FakeDate extends Date { static now() { return now; } }
    const wrap = (arr) => ({ all: () => arr.map((json) => ({ json })), first: () => ({ json: arr[0] }) });
    const $ = (name) => wrap(name === 'Settings' ? [settings] : nodes[name] || []);
    return fn(wrap(input), $, () => state, FakeDate).map((i) => i.json);
  };
}
const queue = node('queue.js');
const build = node('build-emails.js');
const finish = node('finish.js');

let nextId = 1;
const appt = (o = {}) => ({
  Id: `a${nextId++}`, ClientId: 7, ClientName: 'Jane Doe', ClientEmail: 'jane@example.com', Status: 'Confirmed',
  StartDate: T0 + 3 * DAY, DateCreated: T0, LastModified: T0, ServiceName: 'Follow-up', PractitionerName: 'Dr. A',
  LocationName: 'Main', ...o,
});

function started() {
  const state = {};
  assert.deepEqual(queue({ input: [{}], state, now: T0 - 60 * MIN }), []);
  return state;
}

test('first run only sets the cursor', () => {
  const state = {};
  const out = queue({ input: [appt({ DateCreated: T0 - 5 * MIN, LastModified: T0 - 5 * MIN })], state, now: T0 });
  assert.deepEqual(out, []);
  assert.equal(state.cursor, T0);
  assert.deepEqual(state.pending, {});
});

test('a booking is sent once the schedule is quiet for 30 minutes', () => {
  const state = started();
  const a = appt();
  assert.deepEqual(queue({ input: [a], state, now: T0 + 2 * MIN }), []);
  assert.equal(state.pending['7'].dueAt, T0 + 30 * MIN);
  // A later poll sees the same row again (updatedSince is a date): no change to the timer.
  assert.deepEqual(queue({ input: [a], state, now: T0 + 20 * MIN }), []);
  const due = queue({ input: [a], state, now: T0 + 31 * MIN });
  assert.equal(due.length, 1);
  assert.equal(due[0].email, 'jane@example.com');
  assert.deepEqual(state.pending, {});
  assert.deepEqual(queue({ input: [a], state, now: T0 + 40 * MIN }), [], 'never sent twice');
});

test('more bookings or a fix during the wait push the send back', () => {
  const state = started();
  queue({ input: [appt()], state, now: T0 + 2 * MIN });
  queue({ input: [appt({ DateCreated: T0 + 10 * MIN, LastModified: T0 + 10 * MIN })], state, now: T0 + 12 * MIN });
  assert.equal(state.pending['7'].dueAt, T0 + 40 * MIN);
  // A reschedule of an existing appointment (not a new booking) still extends the wait.
  queue({ input: [appt({ DateCreated: T0 - DAY, LastModified: T0 + 25 * MIN })], state, now: T0 + 27 * MIN });
  assert.equal(state.pending['7'].dueAt, T0 + 55 * MIN);
  assert.deepEqual(queue({ input: [], state, now: T0 + 50 * MIN }), []);
  assert.equal(queue({ input: [], state, now: T0 + 56 * MIN }).length, 1);
});

test('edits to clients who are not waiting do not trigger an email', () => {
  const state = started();
  const out = queue({
    input: [
      appt({ DateCreated: T0 - 30 * DAY, LastModified: T0 }), // marked attended / invoiced
      appt({ ClientId: 8, Status: 'Canceled', LastModified: T0 }), // booked and cancelled already
      appt({ ClientId: 9, StartDate: T0 - DAY }), // back-dated entry
    ],
    state, now: T0 + 2 * MIN,
  });
  assert.deepEqual(out, []);
  assert.deepEqual(state.pending, {});
  assert.equal(state.cursor, T0);
});

test('email lists only that client\'s open future appointments, in order', () => {
  const due = [{ clientId: 7, email: 'jane@example.com', name: 'Jane Doe', attempts: 0 }];
  const rows = [
    appt({ Id: 'late', StartDate: T0 + 9 * DAY, ServiceName: 'Later <visit>' }),
    appt({ Id: 'soon', StartDate: T0 + DAY }),
    appt({ Id: 'soon', StartDate: T0 + DAY }), // duplicate row
    appt({ Id: 'pend', StartDate: T0 + 2 * DAY, Status: 'WaitingConfirmation' }),
    appt({ Id: 'cxl', Status: 'Canceled' }),
    appt({ Id: 'past', StartDate: T0 - DAY }),
    appt({ Id: 'other', ClientId: 70, ClientEmail: 'jane@example.com.au' }),
  ];
  const [e] = build({ input: rows, nodes: { 'Queue bookings': due }, now: T0 + 31 * MIN });
  assert.equal(e.count, 3);
  assert.equal(e.to, 'front-desk@example.com');
  assert.match(e.subject, /^\[TEST for Jane Doe <jane@example.com>\] Your upcoming appointments/);
  assert.match(e.html, /Hi Jane,/);
  assert.match(e.html, /Later &lt;visit&gt;/);
  assert.match(e.html, /awaiting confirmation/);
  assert.match(e.html, /Fri, Oct 2, 2026/);
  assert.match(e.html, /10:00 AM/);
  assert.ok(e.html.indexOf('Oct 2,') < e.html.indexOf('Oct 10,'));

  const [live] = build({ input: rows, nodes: { 'Queue bookings': due }, now: T0, settings: { ...SETTINGS, mode: 'live' } });
  assert.equal(live.to, 'jane@example.com');
  assert.equal(live.subject, 'Your upcoming appointments at Movement Solutions');
});

test('no email when everything was cancelled or there is no address', () => {
  const due = [
    { clientId: 7, email: 'jane@example.com', name: 'Jane Doe' },
    { clientId: 8, email: '', name: 'No Email' },
  ];
  const rows = [appt({ Status: 'Canceled' }), appt({ ClientId: 8, ClientEmail: '' })];
  assert.deepEqual(build({ input: rows, nodes: { 'Queue bookings': due }, now: T0 }), []);
});

test('failed sends are retried twice, then given up', () => {
  const state = { cursor: T0, pending: {} };
  const emails = [
    { clientId: 7, email: 'jane@example.com', name: 'Jane', to: 'x', count: 2, attempts: 0 },
    { clientId: 8, email: 'bob@example.com', name: 'Bob', to: 'y', count: 1, attempts: 2 },
    { clientId: 9, email: 'sam@example.com', name: 'Sam', to: 'z', count: 1, attempts: 0 },
  ];
  const out = finish({
    input: [{ error: { message: '429' } }, { error: 'bad contact' }, { messageId: 'm1' }],
    nodes: { 'Build emails': emails }, state, now: T0,
  });
  assert.deepEqual(out.map((r) => r.status), ['failed, will retry', 'failed, gave up', 'sent']);
  assert.deepEqual(Object.keys(state.pending), ['7']);
  assert.equal(state.pending['7'].attempts, 1);
  assert.equal(state.pending['7'].dueAt, T0 + 10 * MIN);
});

test('workflow.json is up to date with the Code node sources', () => {
  const wf = JSON.parse(readFileSync(join(here, 'workflow.json'), 'utf8'));
  const code = Object.fromEntries(wf.nodes.filter((n) => n.parameters.jsCode).map((n) => [n.name, n.parameters.jsCode]));
  assert.equal(code['Queue bookings'], readFileSync(join(here, 'queue.js'), 'utf8'));
  assert.equal(code['Build emails'], readFileSync(join(here, 'build-emails.js'), 'utf8'));
  assert.equal(code['Record results'], readFileSync(join(here, 'finish.js'), 'utf8'));
  assert.equal(wf.active, false);
});
