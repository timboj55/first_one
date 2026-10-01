// Code node "Retries" (run once for all items).
// Puts each failed upload back in the queue so it is tried again about 10 minutes later
// (3 attempts in total). The row is dated so that it falls due 10 minutes from now.
const s = $('Settings').first().json;
const MAX_ATTEMPTS = 3;
const bufferMs = Number(s.bufferMinutes) * 60000;
const pdfs = $('Build PDFs').all().map((i) => i.json);
const results = $('Upload to client file').all().map((i) => i.json);

return pdfs.flatMap((c, i) => {
  const r = results[i] || { error: 'no response' };
  const attempts = (c.attempts || 0) + 1;
  if (!r.error || attempts >= MAX_ATTEMPTS) return [];
  return [{
    json: {
      clientId: String(c.clientId), clientName: c.name || '', clientEmail: c.email || '',
      eventAt: Date.now() - bufferMs + 10 * 60000, isBooking: true, attempts,
    },
  }];
});
