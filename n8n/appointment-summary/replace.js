// Code node "Pick old summaries" (run once for all items).
// For each PDF that uploaded successfully, keeps the patient's newest summary PDF and picks the
// earlier ones (same name apart from the date) for deletion. PracticeQ's upload reply does not
// include the new file's Id, so "newest" is the matching file with the latest DateCreated in
// the list read right after the upload (or the upload's Id, if PracticeQ ever returns one).
// Nothing is deleted when the upload failed or the file list could not be read, and one
// matching file is always kept, so a patient always has a summary.
const pdfs = $('Build PDFs').all().map((i) => i.json);
const uploads = $('Upload to client file').all().map((i) => i.json);
const lists = $('List client files').all().map((i) => i.json);
const escape = (t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const out = [];
pdfs.forEach((c, i) => {
  const up = uploads[i] || {};
  const list = lists[i] || {};
  if (up.error || list.error) return;
  let files;
  try {
    files = typeof list.body === 'string' ? JSON.parse(list.body) : list.body;
  } catch (e) {
    return;
  }
  if (!Array.isArray(files)) return;
  const ours = new RegExp(`^${escape(c.filePrefix)}\\d{4}-\\d{2}-\\d{2}\\.pdf$`);
  const matches = files.filter((f) => f && f.Id && ours.test(f.FileName || ''));
  if (matches.length < 2) return;
  const keep = matches.find((f) => up.Id && f.Id === up.Id)
    || matches.reduce((a, b) => (Number(b.DateCreated) > Number(a.DateCreated) ? b : a));
  for (const f of matches) {
    if (f.Id !== keep.Id) out.push({ json: { clientId: c.uploadTo, fileId: f.Id, fileName: f.FileName } });
  }
});
return out;
