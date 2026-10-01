// Runs the three Code nodes outside n8n with a fake $, $input, static data and clock.
//   node n8n/appointment-summary/test.mjs
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const MIN = 60000;
const T0 = Date.UTC(2026, 9, 1, 14, 0); // 1 Oct 2026, 10:00 ET
const DAY = 24 * 60 * MIN;

const SETTINGS = {
  mode: 'test', testClientId: '999', bufferMinutes: 30, timezone: 'America/New_York',
  practiceName: 'Movement Solutions', practicePhone: '555-0100',
};

function node(file) {
  const body = readFileSync(join(here, file), 'utf8');
  const fn = new Function('$input', '$', '$getWorkflowStaticData', 'Date', body);
  return ({ input = [], nodes = {}, state, now, settings = SETTINGS }) => {
    class FakeDate extends Date { static now() { return now; } }
    const wrap = (arr) => ({ all: () => arr.map((json) => ({ json })), first: () => ({ json: arr[0] }) });
    const $ = (name) => wrap(name === 'Settings' ? [settings] : nodes[name] || []);
    return fn(wrap(input), $, () => state, FakeDate);
  };
}
const json = (run) => (args) => run(args).map((i) => i.json);
const queue = json(node('queue.js'));
const buildRaw = node('build-pdfs.js');
const build = json(buildRaw);
const finish = json(node('finish.js'));
const pickOld = json(node('replace.js'));

function pdfToText(item) {
  const file = join(mkdtempSync(join(tmpdir(), 'summary-')), 'out.pdf');
  writeFileSync(file, Buffer.from(item.binary.data.data, 'base64'));
  return { text: execFileSync('pdftotext', ['-layout', file, '-'], { encoding: 'utf8' }), pages: Number(execFileSync('pdfinfo', [file], { encoding: 'utf8' }).match(/Pages:\s+(\d+)/)[1]) };
}

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

test('PDF lists only that client\'s open future appointments, in order', () => {
  const due = [{ clientId: 7, email: 'jane@example.com', name: 'Jane Doe', attempts: 0 }];
  const rows = [
    appt({ Id: 'late', StartDate: T0 + 9 * DAY, ServiceName: 'Later (visit) – récheck' }),
    appt({ Id: 'soon', StartDate: T0 + DAY }),
    appt({ Id: 'soon', StartDate: T0 + DAY }), // duplicate row
    appt({ Id: 'pend', StartDate: T0 + 2 * DAY, Status: 'WaitingConfirmation' }),
    appt({ Id: 'cxl', Status: 'Canceled', ServiceName: 'Cancelled one' }),
    appt({ Id: 'past', StartDate: T0 - DAY, ServiceName: 'Past one' }),
    appt({ Id: 'other', ClientId: 70, ClientEmail: 'jane@example.com.au', ServiceName: 'Someone else' }),
  ];
  const [item] = buildRaw({ input: rows, nodes: { 'Queue bookings': due }, now: T0 + 31 * MIN });
  assert.equal(item.json.count, 3);
  assert.equal(item.json.uploadTo, '999', 'test mode uploads to the test client');
  assert.equal(item.json.fileName, 'TEST - Jane Doe - Upcoming appointments 2026-10-01.pdf');
  assert.equal(item.json.filePrefix, 'TEST - Jane Doe - Upcoming appointments ');
  assert.equal(item.binary.data.mimeType, 'application/pdf');

  const { text, pages } = pdfToText(item);
  assert.equal(pages, 1);
  assert.match(text, /Upcoming appointments/);
  assert.match(text, /Patient: Jane Doe/);
  assert.match(text, /Fri, Oct 2, 2026\s+10:00 AM\s+Follow-up\s+Dr\. A\s+Main/);
  assert.match(text, /Follow-up \(pending\)/);
  assert.match(text, /Later \(visit\) - récheck/);
  assert.doesNotMatch(text, /Cancelled one|Past one|Someone else/);
  assert.ok(text.indexOf('Oct 2,') < text.indexOf('Oct 3,') && text.indexOf('Oct 3,') < text.indexOf('Oct 10,'));
  assert.match(text, /3 upcoming appointments\. If anything looks wrong, please call us at 555-0100\./);

  const [live] = build({ input: rows, nodes: { 'Queue bookings': due }, now: T0, settings: { ...SETTINGS, mode: 'live' } });
  assert.equal(live.uploadTo, 7);
  assert.equal(live.fileName, 'Upcoming appointments 2026-10-01.pdf');
});

test('long schedules continue on a second page', () => {
  const due = [{ clientId: 7, name: 'Jane Doe' }];
  const rows = Array.from({ length: 40 }, (_, i) => appt({ Id: `p${i}`, StartDate: T0 + (i + 1) * DAY }));
  const [item] = buildRaw({ input: rows, nodes: { 'Queue bookings': due }, now: T0 });
  const { text, pages } = pdfToText(item);
  assert.equal(pages, 2);
  assert.equal((text.match(/Follow-up/g) || []).length, 40);
  assert.match(text, /40 upcoming appointments/);
});

test('no PDF when everything was cancelled', () => {
  const due = [{ clientId: 7, email: 'jane@example.com', name: 'Jane Doe' }];
  assert.deepEqual(build({ input: [appt({ Status: 'Canceled' })], nodes: { 'Queue bookings': due }, now: T0 }), []);
});

test('failed uploads are retried twice, then given up', () => {
  const state = { cursor: T0, pending: {} };
  const pdfs = [
    { clientId: 7, email: 'jane@example.com', name: 'Jane', uploadTo: 7, count: 2, attempts: 0 },
    { clientId: 8, email: 'bob@example.com', name: 'Bob', uploadTo: 8, count: 1, attempts: 2 },
    { clientId: 9, email: 'sam@example.com', name: 'Sam', uploadTo: 9, count: 1, attempts: 0 },
  ];
  const out = finish({
    nodes: { 'Build PDFs': pdfs, 'Upload to client file': [{ error: { message: '429' } }, { error: 'not found' }, { Id: 'f1' }] }, state, now: T0,
  });
  assert.deepEqual(out.map((r) => r.status), ['failed, will retry', 'failed, gave up', 'uploaded']);
  assert.deepEqual(Object.keys(state.pending), ['7']);
  assert.equal(state.pending['7'].attempts, 1);
  assert.equal(state.pending['7'].dueAt, T0 + 10 * MIN);
});

test('older summaries are deleted only after the new one uploads', () => {
  const pdfs = [
    { uploadTo: 7, filePrefix: 'Upcoming appointments ' },
    { uploadTo: 8, filePrefix: 'Upcoming appointments ' }, // upload failed
    { uploadTo: 9, filePrefix: 'Upcoming appointments ' }, // list failed
    { uploadTo: 999, filePrefix: 'TEST - Jane (Doe) - Upcoming appointments ' },
  ];
  const files7 = [
    { Id: 'new', FileName: 'Upcoming appointments 2026-10-01.pdf' },
    { Id: 'old1', FileName: 'Upcoming appointments 2026-09-20.pdf' },
    { Id: 'same-day', FileName: 'Upcoming appointments 2026-10-01.pdf' },
    { Id: 'intake', FileName: 'Intake form.pdf' },
    { Id: 'copy', FileName: 'Upcoming appointments 2026-09-20 (signed).pdf' },
    { Id: 'staff', FileName: 'Old upcoming appointments 2026-09-01.pdf' },
  ];
  const files999 = [
    { Id: 't-new', FileName: 'TEST - Jane (Doe) - Upcoming appointments 2026-10-01.pdf' },
    { Id: 't-old', FileName: 'TEST - Jane (Doe) - Upcoming appointments 2026-09-30.pdf' },
    { Id: 't-other', FileName: 'TEST - Bob - Upcoming appointments 2026-09-30.pdf' },
  ];
  const out = pickOld({
    nodes: {
      'Build PDFs': pdfs,
      'Upload to client file': [{ Id: 'new' }, { error: 'boom' }, { Id: 'n9' }, { Id: 't-new' }],
      'List client files': [
        { body: JSON.stringify(files7) },
        { body: JSON.stringify([{ Id: 'x', FileName: 'Upcoming appointments 2026-09-01.pdf' }]) },
        { error: { message: '500' } },
        { body: JSON.stringify(files999) },
      ],
    },
  });
  assert.deepEqual(out.map((r) => [r.clientId, r.fileId]), [[7, 'old1'], [7, 'same-day'], [999, 't-old']]);
});

test('workflow.json is up to date with the Code node sources', () => {
  const wf = JSON.parse(readFileSync(join(here, 'workflow.json'), 'utf8'));
  const code = Object.fromEntries(wf.nodes.filter((n) => n.parameters.jsCode).map((n) => [n.name, n.parameters.jsCode]));
  assert.equal(code['Queue bookings'], readFileSync(join(here, 'queue.js'), 'utf8'));
  assert.equal(code['Build PDFs'], readFileSync(join(here, 'build-pdfs.js'), 'utf8'));
  assert.equal(code['Record results'], readFileSync(join(here, 'finish.js'), 'utf8'));
  assert.equal(code['Pick old summaries'], readFileSync(join(here, 'replace.js'), 'utf8'));
  assert.equal(wf.active, false);
});
