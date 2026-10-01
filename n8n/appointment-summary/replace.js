// Code node "Pick old summaries" (run once for all items).
// For each PDF that uploaded successfully, picks the patient's earlier summary PDFs (same
// name apart from the date) for deletion. Nothing is deleted when the upload failed or the
// file list could not be read, so a patient always keeps at least one summary.
const pdfs = $('Build PDFs').all().map((i) => i.json);
const uploads = $('Upload to client file').all().map((i) => i.json);
const lists = $('List client files').all().map((i) => i.json);
const escape = (t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const out = [];
pdfs.forEach((c, i) => {
  const up = uploads[i] || {};
  const list = lists[i] || {};
  if (up.error || !up.Id || list.error) return;
  let files;
  try {
    files = typeof list.body === 'string' ? JSON.parse(list.body) : list.body;
  } catch (e) {
    return;
  }
  if (!Array.isArray(files)) return;
  const ours = new RegExp(`^${escape(c.filePrefix)}\\d{4}-\\d{2}-\\d{2}\\.pdf$`);
  for (const f of files) {
    if (f && f.Id && f.Id !== up.Id && ours.test(f.FileName || '')) {
      out.push({ json: { clientId: c.uploadTo, fileId: f.Id, fileName: f.FileName } });
    }
  }
});
return out;
