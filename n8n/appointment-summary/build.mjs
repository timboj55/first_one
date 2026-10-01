// Assembles workflow.json (importable into n8n) from the Code node sources in this folder.
// Run after editing any .js file:  node n8n/appointment-summary/build.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = (f) => readFileSync(join(here, f), 'utf8');

const IQ = { httpHeaderAuth: { id: '', name: 'PracticeQ API (X-Auth-Key)' } };
const GHL = { httpHeaderAuth: { id: '', name: 'GHL Private Integration (Bearer)' } };
const auth = { authentication: 'genericCredentialType', genericAuthType: 'httpHeaderAuth' };
const setting = (name, value, type = 'string') => ({ id: `setting-${name}`, name, value, type });

const nodes = [
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
          setting('testEmail', 'CHANGE-ME@example.com'),
          setting('bufferMinutes', 30, 'number'),
          setting('timezone', 'America/New_York'),
          setting('practiceName', 'Movement Solutions'),
          setting('practicePhone', 'CHANGE-ME'),
          setting('ghlLocationId', 'CHANGE-ME'),
        ],
      },
      options: {},
    },
  },
  {
    id: 'summary-get-changed', name: 'Get changed appointments', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [440, 0], alwaysOutputData: true, retryOnFail: true, maxTries: 3, waitBetweenTries: 5000,
    credentials: IQ,
    parameters: {
      url: 'https://intakeq.com/api/v1/appointments', ...auth,
      sendQuery: true,
      queryParameters: {
        parameters: [
          { name: 'updatedSince', value: "={{ $now.setZone($('Settings').first().json.timezone).minus({ days: 1 }).toFormat('yyyy-MM-dd') }}" },
        ],
      },
      options: {
        pagination: {
          pagination: {
            parameters: { parameters: [{ name: 'page', value: '={{ $pageCount + 1 }}' }] },
            paginationCompleteWhen: 'other',
            completeExpression: '={{ $response.body.length < 100 }}',
            limitPagesFetched: true,
            maxRequests: 20,
            requestInterval: 3500,
          },
        },
      },
    },
  },
  {
    id: 'summary-queue', name: 'Queue bookings', type: 'n8n-nodes-base.code', typeVersion: 2, position: [660, 0],
    parameters: { jsCode: src('queue.js') },
  },
  {
    id: 'summary-get-upcoming', name: 'Get upcoming', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [880, 0], retryOnFail: true, maxTries: 3, waitBetweenTries: 5000,
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
      options: { batching: { batch: { batchSize: 1, batchInterval: 3500 } } },
    },
  },
  {
    id: 'summary-build', name: 'Build emails', type: 'n8n-nodes-base.code', typeVersion: 2, position: [1100, 0],
    parameters: { jsCode: src('build-emails.js') },
  },
  {
    id: 'summary-ghl-contact', name: 'Find GHL contact', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [1320, 0], onError: 'continueRegularOutput', retryOnFail: true, maxTries: 2, waitBetweenTries: 3000,
    credentials: GHL,
    parameters: {
      method: 'POST', url: 'https://services.leadconnectorhq.com/contacts/upsert', ...auth,
      sendHeaders: true,
      headerParameters: { parameters: [{ name: 'Version', value: '2021-07-28' }] },
      sendBody: true, specifyBody: 'json',
      jsonBody: "={{ JSON.stringify({ locationId: $('Settings').first().json.ghlLocationId, email: $json.to }) }}",
      options: {},
    },
  },
  {
    id: 'summary-ghl-send', name: 'Send email', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [1540, 0], onError: 'continueRegularOutput',
    credentials: GHL,
    parameters: {
      method: 'POST', url: 'https://services.leadconnectorhq.com/conversations/messages', ...auth,
      sendHeaders: true,
      headerParameters: { parameters: [{ name: 'Version', value: '2021-04-15' }] },
      sendBody: true, specifyBody: 'json',
      jsonBody: "={{ JSON.stringify({ type: 'Email', contactId: $json.contact && $json.contact.id, subject: $('Build emails').item.json.subject, html: $('Build emails').item.json.html }) }}",
      options: {},
    },
  },
  {
    id: 'summary-finish', name: 'Record results', type: 'n8n-nodes-base.code', typeVersion: 2, position: [1760, 0],
    parameters: { jsCode: src('finish.js') },
  },
];

const chain = nodes.map((n) => n.name);
const connections = Object.fromEntries(
  chain.slice(0, -1).map((name, i) => [name, { main: [[{ node: chain[i + 1], type: 'main', index: 0 }]] }]),
);

const workflow = {
  name: 'PracticeQ booking summary email',
  nodes,
  connections,
  settings: { executionOrder: 'v1' },
  active: false,
};
writeFileSync(join(here, 'workflow.json'), JSON.stringify(workflow, null, 2) + '\n');
console.log('wrote workflow.json');
