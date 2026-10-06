// Runs the Code nodes outside n8n with a fake $, $input, data table and clock.
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
  practiceName: 'Movement Solutions', practicePhone: '555-0100', afterCloseMinutes: 60,
  businessHours: JSON.stringify({
    mon: ['08:00', '17:00'], tue: ['08:00', '17:00'], wed: ['08:00', '17:00'], thu: ['08:00', '17:00'],
    fri: ['08:00', '16:00'], sat: null, sun: null,
  }),
  holidays: '2026-11-26,2026-12-25',
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
const classify = json(node('classify.js'));
const hours = json(node('hours.js'));
const duePatients = json(node('due.js'));
const keepDue = json(node('keep-due.js'));
const retries = json(node('retries.js'));
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

// PracticeQ webhook payload as forwarded by the existing workflow ($json.body).
const event = (type, o = {}) => ({ body: { EventType: type, ClientId: 7, Appointment: appt(o) } });

// In-memory stand-in for the booking_summary_queue data table plus one sweeper run.
function harness() {
  const table = [];
  return {
    table,
    receive(ev, now) { table.push(...classify({ input: [ev], now })); },
    sweep(now) {
      const due = duePatients({ input: [...table], now });
      for (const d of due) {
        for (let i = table.length - 1; i >= 0; i--) {
          if (table[i].clientId === d.clientId && table[i].eventAt <= d.upTo) table.splice(i, 1);
        }
      }
      return keepDue({ nodes: { 'Due patients': due }, now });
    },
  };
}

test('only a new, open, future appointment counts as a booking', () => {
  const at = (ev) => classify({ input: [ev], now: T0 })[0];
  assert.deepEqual(at(event('AppointmentCreated')), {
    clientId: '7', clientName: 'Jane Doe', clientEmail: 'jane@example.com', eventAt: T0, isBooking: true, attempts: 0,
  });
  assert.equal(at(event('AppointmentCreated', { Status: 'WaitingConfirmation' })).isBooking, true);
  assert.equal(at(event('AppointmentRescheduled')).isBooking, false);
  assert.equal(at(event('AppointmentCanceled', { Status: 'Canceled' })).isBooking, false);
  assert.equal(at(event('AppointmentCreated', { StartDate: T0 - DAY })).isBooking, false, 'back-dated entry');
  assert.equal(at(event('AppointmentCreated').body).isBooking, true, 'accepts the bare payload too');
  assert.deepEqual(classify({ input: [{ body: { EventType: 'AppointmentCreated' } }], now: T0 }), []);
});

test('a booking gets one PDF once the schedule is quiet for 30 minutes', () => {
  const h = harness();
  h.receive(event('AppointmentCreated'), T0);
  h.receive(event('AppointmentCreated'), T0 + 10 * MIN); // second visit booked
  h.receive(event('AppointmentRescheduled'), T0 + 25 * MIN); // mistake fixed
  assert.deepEqual(h.sweep(T0 + 50 * MIN), []);
  const due = h.sweep(T0 + 55 * MIN);
  assert.deepEqual(due.map((d) => [d.clientId, d.name, d.email, d.upTo]), [['7', 'Jane Doe', 'jane@example.com', T0 + 25 * MIN]]);
  assert.deepEqual(h.table, []);
  assert.deepEqual(h.sweep(T0 + 60 * MIN), [], 'never twice');
});

test('changes for a patient without a new booking are dropped', () => {
  const h = harness();
  h.receive(event('AppointmentCanceled', { Status: 'Canceled' }), T0);
  h.receive(event('AppointmentMissed', { ClientId: 8 }), T0);
  assert.deepEqual(h.sweep(T0 + 31 * MIN), []);
  assert.deepEqual(h.table, []);
});

test('an event arriving during a run stays queued for the next round', () => {
  const h = harness();
  h.receive(event('AppointmentCreated'), T0);
  const due = duePatients({ input: [...h.table], now: T0 + 31 * MIN });
  h.receive(event('AppointmentCreated'), T0 + 32 * MIN); // lands between "Read queue" and "Remove from queue"
  for (let i = h.table.length - 1; i >= 0; i--) if (h.table[i].eventAt <= due[0].upTo) h.table.splice(i, 1);
  assert.equal(h.table.length, 1);
  assert.equal(h.sweep(T0 + 63 * MIN).length, 1);
});

test('at most 10 PDFs per run, oldest first', () => {
  const rows = Array.from({ length: 12 }, (_, i) => ({ clientId: String(i), eventAt: T0 + i, isBooking: true }));
  const out = duePatients({ input: rows, now: T0 + 60 * MIN });
  assert.deepEqual(out.map((r) => r.clientId), ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']);
});

test('runs only in business hours plus one hour, never on holidays', () => {
  const et = (iso) => Date.parse(iso); // all times below are Eastern (EDT, -04:00 / EST, -05:00)
  const open = (iso) => hours({ input: [{}], now: et(iso) }).length === 1;
  assert.equal(open('2026-10-01T07:59:00-04:00'), false, 'Thu before opening');
  assert.equal(open('2026-10-01T08:00:00-04:00'), true, 'Thu opening');
  assert.equal(open('2026-10-01T17:30:00-04:00'), true, 'Thu, within the hour after closing');
  assert.equal(open('2026-10-01T18:00:00-04:00'), false, 'Thu, 1 hour after closing');
  assert.equal(open('2026-10-02T16:59:00-04:00'), true, 'Fri closes at 4, so open until 5');
  assert.equal(open('2026-10-02T17:00:00-04:00'), false);
  assert.equal(open('2026-10-03T12:00:00-04:00'), false, 'Saturday');
  assert.equal(open('2026-11-26T12:00:00-05:00'), false, 'Thanksgiving');
  assert.equal(open('2026-11-27T12:00:00-05:00'), true);
});

test('after-hours bookings wait for the next opening', () => {
  const h = harness();
  const fri9pm = Date.parse('2026-10-02T21:00:00-04:00');
  h.receive(event('AppointmentCreated'), fri9pm);
  const sweepIfOpen = (now) => (hours({ input: [{}], now }).length ? h.sweep(now) : []);
  assert.deepEqual(sweepIfOpen(Date.parse('2026-10-03T10:00:00-04:00')), []); // Saturday
  assert.equal(sweepIfOpen(Date.parse('2026-10-05T08:00:00-04:00')).length, 1); // Monday 8am
});

test('PDF lists only that client\'s open future appointments, in order', () => {
  const due = [{ clientId: 7, email: 'jane@example.com', name: 'Jane Doe', attempts: 0 }];
  const rows = [
    appt({ Id: 'late', StartDate: T0 + 9 * DAY }),
    appt({ Id: 'soon', StartDate: T0 + DAY }),
    appt({ Id: 'soon', StartDate: T0 + DAY }), // duplicate row
    appt({ Id: 'pend', StartDate: T0 + 2 * DAY, Status: 'WaitingConfirmation' }),
    appt({ Id: 'cxl', Status: 'Canceled', ServiceName: 'Cancelled one' }),
    appt({ Id: 'past', StartDate: T0 - DAY, ServiceName: 'Past one' }),
    appt({ Id: 'other', ClientId: 70, ClientEmail: 'jane@example.com.au', ServiceName: 'Someone else' }),
  ];
  const [item] = buildRaw({ input: rows, nodes: { 'Keep due': due }, now: T0 + 31 * MIN });
  assert.equal(item.json.count, 3);
  assert.equal(item.json.uploadTo, '999', 'test mode uploads to the test client');
  assert.equal(item.json.fileName, 'TEST - Jane Doe - Upcoming appointments 2026-10-01.pdf');
  assert.equal(item.json.filePrefix, 'TEST - Jane Doe - Upcoming appointments ');
  assert.equal(item.binary.data.mimeType, 'application/pdf');

  const { text, pages } = pdfToText(item);
  assert.equal(pages, 1);
  assert.match(text, /Upcoming appointments/);
  assert.match(text, /Patient: Jane Doe/);
  assert.match(text, /Date\s+Time\n/);
  assert.match(text, /Fri, Oct 2, 2026\s+10:00 AM\n/);
  assert.doesNotMatch(text, /Dr\. A|With|Follow-up|Visit|Main|Location/, 'no provider, visit type or location');
  assert.match(text, /Sat, Oct 3, 2026\s+10:00 AM \(pending confirmation\)/);
  assert.doesNotMatch(text, /Cancelled one|Past one|Someone else/);
  assert.ok(text.indexOf('Oct 2,') < text.indexOf('Oct 3,') && text.indexOf('Oct 3,') < text.indexOf('Oct 10,'));
  assert.match(text, /3 upcoming appointments\. If anything looks wrong, please call us at 555-0100\./);

  const [live] = build({ input: rows, nodes: { 'Keep due': due }, now: T0, settings: { ...SETTINGS, mode: 'live' } });
  assert.equal(live.uploadTo, 7);
  assert.equal(live.fileName, 'Upcoming appointments 2026-10-01.pdf');
});

test('patients in liveClientIds get real PDFs while in test mode', () => {
  const due = [{ clientId: '7', name: 'Jane Doe' }, { clientId: '8', name: 'Bob Roe' }];
  const rows = [appt({ ClientId: 7 }), appt({ ClientId: 8 })];
  const out = build({ input: rows, nodes: { 'Keep due': due }, now: T0, settings: { ...SETTINGS, liveClientIds: ' 7 , 12' } });
  assert.deepEqual(out.map((o) => [o.clientId, o.uploadTo, o.fileName]), [
    ['7', '7', 'Upcoming appointments 2026-10-01.pdf'],
    ['8', '999', 'TEST - Bob Roe - Upcoming appointments 2026-10-01.pdf'],
  ]);
});

test('long schedules continue on a second page', () => {
  const due = [{ clientId: 7, name: 'Zoë (Test) – O’Neil' }];
  const rows = Array.from({ length: 40 }, (_, i) => appt({ Id: `p${i}`, StartDate: T0 + (i + 1) * DAY }));
  const [item] = buildRaw({ input: rows, nodes: { 'Keep due': due }, now: T0 });
  const { text, pages } = pdfToText(item);
  assert.equal(pages, 2);
  assert.equal((text.match(/[A-Z][a-z]{2}, [A-Z][a-z]{2} \d+, 2026/g) || []).length, 40); // one per row
  assert.match(text, /40 upcoming appointments/);
  assert.match(text, /Patient: Zoë \(Test\) - O'Neil/, 'accents kept, parentheses escaped, dashes/quotes simplified');
});

test('no PDF when everything was cancelled', () => {
  const due = [{ clientId: 7, email: 'jane@example.com', name: 'Jane Doe' }];
  assert.deepEqual(build({ input: [appt({ Status: 'Canceled' })], nodes: { 'Keep due': due }, now: T0 }), []);
});

test('failed uploads are logged and re-queued twice, then given up', () => {
  const pdfs = [
    { clientId: '7', email: 'jane@example.com', name: 'Jane', uploadTo: '7', count: 2, attempts: 0 },
    { clientId: '8', email: 'bob@example.com', name: 'Bob', uploadTo: '8', count: 1, attempts: 2 },
    { clientId: '9', email: 'sam@example.com', name: 'Sam', uploadTo: '9', count: 1, attempts: 0 },
  ];
  const nodes = { 'Build PDFs': pdfs, 'Upload to client file': [{ error: { message: '429' } }, { error: 'not found' }, { Id: 'f1' }] };
  assert.deepEqual(finish({ nodes, now: T0 }).map((r) => r.status), ['failed', 'failed', 'uploaded']);
  const again = retries({ nodes, now: T0 });
  assert.deepEqual(again, [{
    clientId: '7', clientName: 'Jane', clientEmail: 'jane@example.com', eventAt: T0 - 20 * MIN, isBooking: true, attempts: 1,
  }]);
  // ...which the sweeper picks up 10 minutes later.
  assert.deepEqual(duePatients({ input: again, now: T0 + 9 * MIN }), []);
  assert.equal(duePatients({ input: again, now: T0 + 10 * MIN })[0].attempts, 1);
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

test('without an Id in the upload reply, the newest file is kept (PracticeQ behaviour seen 5 Oct)', () => {
  const prefix = 'TEST - Joseph Wells - Upcoming appointments ';
  const files = [
    { Id: 'a', DateCreated: 100, FileName: `${prefix}2026-10-05.pdf` },
    { Id: 'b', DateCreated: 300, FileName: `${prefix}2026-10-05.pdf` },
    { Id: 'c', DateCreated: 200, FileName: `${prefix}2026-10-05.pdf` },
    { Id: 'd', DateCreated: 400, FileName: 'TEST - Dorie Giuliano - Upcoming appointments 2026-10-05.pdf' },
  ];
  const run = (upload, list) => pickOld({ nodes: {
    'Build PDFs': [{ uploadTo: '2425', filePrefix: prefix }],
    'Upload to client file': [upload],
    'List client files': [list],
  } }).map((r) => r.fileId);
  assert.deepEqual(run({}, { body: JSON.stringify(files) }), ['a', 'c']);
  assert.deepEqual(run({ error: 'boom' }, { body: JSON.stringify(files) }), [], 'failed upload deletes nothing');
  assert.deepEqual(run({}, { body: JSON.stringify(files.slice(0, 1)) }), [], 'a single file is never deleted');
  assert.deepEqual(run({}, { body: 'not json' }), []);
});

test('workflow.json is up to date with the Code node sources', () => {
  const wf = JSON.parse(readFileSync(join(here, 'workflow.json'), 'utf8'));
  const code = Object.fromEntries(wf.nodes.filter((n) => n.parameters.jsCode).map((n) => [n.name, n.parameters.jsCode]));
  assert.equal(code['Build PDFs'], readFileSync(join(here, 'build-pdfs.js'), 'utf8'));
  for (const [name, file] of [['Classify event', 'classify.js'], ['Business hours?', 'hours.js'], ['Due patients', 'due.js'],
    ['Keep due', 'keep-due.js'], ['Retries', 'retries.js']]) {
    assert.equal(code[name], readFileSync(join(here, file), 'utf8'));
  }
  assert.equal(code['Record results'], readFileSync(join(here, 'finish.js'), 'utf8'));
  assert.equal(code['Pick old summaries'], readFileSync(join(here, 'replace.js'), 'utf8'));
  assert.equal(wf.active, false);
});
