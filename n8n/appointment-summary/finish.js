// Code node "Record results" (run once for all items).
// Reads the PracticeQ upload responses, one per "Build PDFs" item in the same order (the
// upload node continues on error, so a failure is an item with an `error` field). Output is a
// log line per PDF, visible in the n8n execution.
const pdfs = $('Build PDFs').all().map((i) => i.json);
const results = $('Upload to client file').all().map((i) => i.json);

return pdfs.map((c, i) => {
  const r = results[i] || { error: 'no response' };
  const base = { clientId: c.clientId, uploadedTo: c.uploadTo, file: c.fileName, appointments: c.count };
  if (!r.error) return { json: { ...base, status: 'uploaded', fileId: r.Id || null } };
  const error = typeof r.error === 'string' ? r.error : (r.error.message || JSON.stringify(r.error));
  return { json: { ...base, status: 'failed', attempt: (c.attempts || 0) + 1, error } };
});
