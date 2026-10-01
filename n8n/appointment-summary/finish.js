// Code node "Record results" (run once for all items).
// Reads the PracticeQ upload responses, one per "Build PDFs" item in the same order (the
// upload node continues on error, so a failure is an item with an `error` field).
// A failed upload is retried 10 minutes later, up to 3 attempts in total. Output is a log line
// per PDF, visible in the n8n execution.
const state = $getWorkflowStaticData('global');
state.pending = state.pending || {};
const pdfs = $('Build PDFs').all().map((i) => i.json);
const results = $('Upload to client file').all().map((i) => i.json);
const MAX_ATTEMPTS = 3;

return pdfs.map((c, i) => {
  const r = results[i] || { error: 'no response' };
  const base = { clientId: c.clientId, uploadedTo: c.uploadTo, file: c.fileName, appointments: c.count };
  if (!r.error) return { json: { ...base, status: 'uploaded', fileId: r.Id || null } };

  const attempts = (c.attempts || 0) + 1;
  const key = String(c.clientId);
  const retry = attempts < MAX_ATTEMPTS;
  if (retry && !state.pending[key]) {
    state.pending[key] = { clientId: c.clientId, email: c.email, name: c.name, dueAt: Date.now() + 10 * 60000, attempts };
  }
  const error = typeof r.error === 'string' ? r.error : (r.error.message || JSON.stringify(r.error));
  return { json: { ...base, status: retry ? 'failed, will retry' : 'failed, gave up', attempts, error } };
});
