// Assembles workflow.json (importable into n8n) from the Code node sources in this folder.
// Run after editing any .js file:  node n8n/appointment-summary/build.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = (f) => readFileSync(join(here, f), 'utf8');

const IQ = { httpHeaderAuth: { id: '', name: 'PracticeQ API (X-Auth-Key)' } };
const auth = { authentication: 'genericCredentialType', genericAuthType: 'httpHeaderAuth' };
const KEY = { httpHeaderAuth: { id: '', name: 'Booking summary webhook key' } };
const QUEUE = { __rl: true, mode: 'name', value: 'booking_summary_queue' };
const setting = (name, value, type = 'string') => ({ id: `setting-${name}`, name, value, type });
const code = (id, name, file, position) => ({
  id, name, type: 'n8n-nodes-base.code', typeVersion: 2, position, parameters: { jsCode: src(file) },
});
const paced = { batching: { batch: { batchSize: 1, batchInterval: 3500 } } };

// Business hours from agent_config.json (the practice's GHL lead agent uses the same table).
const config = JSON.parse(readFileSync(join(here, '../../agent_config.json'), 'utf8'));
const businessHours = JSON.stringify(config.hours.business);
const holidays = config.hours.holidays.join(',');

const nodes = [
  // ---- webhook branch: queue every appointment event ------------------------------------
  {
    id: 'summary-webhook', name: 'Appointment event', type: 'n8n-nodes-base.webhook', typeVersion: 2,
    position: [0, -300], webhookId: '5b0f6a3e-2d7c-4c1e-9a43-7d2b8c1e0f55',
    credentials: KEY,
    parameters: { httpMethod: 'POST', path: 'booking-summary', authentication: 'headerAuth', responseMode: 'onReceived', options: {} },
  },
  code('summary-classify', 'Classify event', 'classify.js', [220, -300]),
  {
    id: 'summary-enqueue', name: 'Add to queue', type: 'n8n-nodes-base.dataTable', typeVersion: 1.1, position: [440, -300],
    parameters: { resource: 'row', operation: 'insert', dataTableId: QUEUE, columns: { mappingMode: 'autoMapInputData', value: null } },
  },

  // ---- sweeper branch: business hours only ------------------------------------------------
  {
    id: 'summary-schedule', name: 'Every 5 minutes', type: 'n8n-nodes-base.scheduleTrigger', typeVersion: 1.2,
    position: [0, 0],
    parameters: { rule: { interval: [{ field: 'minutes', minutesInterval: 5 }] } },
  },
  {
    id: 'summary-settings', name: 'Settings', type: 'n8n-nodes-base.set', typeVersion: 3.4, position: [220, 0],
    parameters: {
      assignments: {
        assignments: [
          setting('mode', 'test'),
          setting('testClientId', 'CHANGE-ME'),
          setting('liveClientIds', ''),
          setting('bufferMinutes', 5, 'number'),
          setting('timezone', 'America/New_York'),
          setting('businessHours', businessHours),
          setting('afterCloseMinutes', 60, 'number'),
          setting('holidays', holidays),
          setting('practiceName', 'Movement Solutions'),
          setting('practicePhone', 'CHANGE-ME'),
        ],
      },
      options: {},
    },
  },
  code('summary-hours', 'Business hours?', 'hours.js', [440, 0]),
  {
    id: 'summary-read-queue', name: 'Read queue', type: 'n8n-nodes-base.dataTable', typeVersion: 1.1, position: [660, 0],
    parameters: { resource: 'row', operation: 'get', dataTableId: QUEUE, matchType: 'anyCondition', filters: {}, returnAll: true },
  },
  code('summary-due', 'Due patients', 'due.js', [880, 0]),
  {
    id: 'summary-dequeue', name: 'Remove from queue', type: 'n8n-nodes-base.dataTable', typeVersion: 1.1,
    position: [1100, 0], alwaysOutputData: true,
    parameters: {
      resource: 'row', operation: 'deleteRows', dataTableId: QUEUE, matchType: 'allConditions',
      filters: {
        conditions: [
          { keyName: 'clientId', condition: 'eq', keyValue: '={{ $json.clientId }}' },
          { keyName: 'eventAt', condition: 'lte', keyValue: '={{ $json.upTo }}' },
        ],
      },
      options: {},
    },
  },
  code('summary-keep-due', 'Keep due', 'keep-due.js', [1320, 0]),
  {
    id: 'summary-get-upcoming', name: 'Get upcoming', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [1540, 0], retryOnFail: true, maxTries: 3, waitBetweenTries: 5000,
    credentials: IQ,
    parameters: {
      url: 'https://intakeq.com/api/v1/appointments', ...auth,
      sendQuery: true,
      queryParameters: {
        parameters: [
          { name: 'client', value: '={{ $json.email || $json.name }}' },
          { name: 'startDate', value: "={{ $now.setZone($('Settings').first().json.timezone).toFormat('yyyy-MM-dd') }}" },
        ],
      },
      options: paced,
    },
  },
  code('summary-build', 'Build PDFs', 'build-pdfs.js', [1760, 0]),
  {
    id: 'summary-upload', name: 'Upload to client file', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [1980, 0], onError: 'continueRegularOutput', retryOnFail: true, maxTries: 2, waitBetweenTries: 5000,
    credentials: IQ,
    parameters: {
      method: 'POST', url: '=https://intakeq.com/api/v1/files/{{ $json.uploadTo }}', ...auth,
      sendBody: true, contentType: 'multipart-form-data',
      bodyParameters: { parameters: [{ parameterType: 'formBinaryData', name: 'file', inputDataFieldName: 'data' }] },
      options: paced,
    },
  },
  {
    id: 'summary-list-files', name: 'List client files', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [2200, 0], onError: 'continueRegularOutput', retryOnFail: true, maxTries: 2, waitBetweenTries: 5000,
    credentials: IQ,
    parameters: {
      url: 'https://intakeq.com/api/v1/files', ...auth,
      sendQuery: true,
      queryParameters: { parameters: [{ name: 'clientId', value: "={{ $('Build PDFs').item.json.uploadTo }}" }] },
      options: {
        // Text keeps one output item per client (a JSON array would be split into items).
        response: { response: { responseFormat: 'text', outputPropertyName: 'body' } },
        ...paced,
      },
    },
  },
  code('summary-finish', 'Record results', 'finish.js', [2420, 0]),
  code('summary-pick-old', 'Pick old summaries', 'replace.js', [2640, -120]),
  {
    id: 'summary-delete-old', name: 'Delete old summary', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [2860, -120], onError: 'continueRegularOutput',
    credentials: IQ,
    parameters: { method: 'DELETE', url: '=https://intakeq.com/api/v1/files/{{ $json.fileId }}', ...auth, options: paced },
  },
  code('summary-retries', 'Retries', 'retries.js', [2640, 120]),
  {
    id: 'summary-requeue', name: 'Re-queue failed', type: 'n8n-nodes-base.dataTable', typeVersion: 1.1, position: [2860, 120],
    parameters: { resource: 'row', operation: 'insert', dataTableId: QUEUE, columns: { mappingMode: 'autoMapInputData', value: null } },
  },
];

const links = [
  ['Appointment event', 'Classify event'], ['Classify event', 'Add to queue'],
  ['Every 5 minutes', 'Settings'], ['Settings', 'Business hours?'], ['Business hours?', 'Read queue'],
  ['Read queue', 'Due patients'], ['Due patients', 'Remove from queue'], ['Remove from queue', 'Keep due'],
  ['Keep due', 'Get upcoming'], ['Get upcoming', 'Build PDFs'], ['Build PDFs', 'Upload to client file'],
  ['Upload to client file', 'List client files'], ['List client files', 'Record results'],
  ['Record results', 'Pick old summaries'], ['Pick old summaries', 'Delete old summary'],
  ['Record results', 'Retries'], ['Retries', 'Re-queue failed'],
];
const connections = {};
for (const [from, to] of links) {
  connections[from] = connections[from] || { main: [[]] };
  connections[from].main[0].push({ node: to, type: 'main', index: 0 });
}

// Node to paste into the existing "IntakeQ Appointments -> GHL" workflow, wired straight off
// its PracticeQ webhook node. It forwards each event and never stops that workflow.
const forward = {
  nodes: [{
    id: 'forward-booking-summary', name: 'Forward to booking summary', type: 'n8n-nodes-base.httpRequest',
    typeVersion: 4.2, position: [0, 0], onError: 'continueRegularOutput', credentials: KEY,
    parameters: {
      method: 'POST', url: 'https://YOUR-N8N-HOST/webhook/booking-summary', ...auth,
      sendBody: true, specifyBody: 'json', jsonBody: '={{ JSON.stringify($json.body) }}',
      options: { timeout: 10000 },
    },
  }],
  connections: {},
};
writeFileSync(join(here, 'forward-node.json'), JSON.stringify(forward, null, 2) + '\n');

const workflow = {
  name: 'PracticeQ booking summary PDF',
  nodes,
  connections,
  settings: { executionOrder: 'v1' },
  active: false,
};
writeFileSync(join(here, 'workflow.json'), JSON.stringify(workflow, null, 2) + '\n');
console.log('wrote workflow.json');
