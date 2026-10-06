// Code node "Build PDFs" (run once for all items).
// Input: every appointment from today on for each due client (from "Get upcoming").
// Output: one item per PDF to upload, with the PracticeQ client to upload to and the PDF as
// binary property `data`. The PDF is written by hand (Helvetica, US Letter) so the workflow
// needs no PDF library on the n8n server.
const s = $('Settings').first().json;
const due = $('Keep due').all().map((i) => i.json);
const rows = $input.all().map((i) => i.json).filter((r) => r && r.Id);
const OPEN = ['Confirmed', 'WaitingConfirmation'];
const now = Date.now();
// In test mode, patients listed in `liveClientIds` (comma-separated) already get real PDFs.
const liveIds = String(s.liveClientIds || '').split(',').map((x) => x.trim()).filter(Boolean);
const isLive = (c) => s.mode === 'live' || liveIds.includes(String(c.clientId));

const fmt = (ms, opts) => new Intl.DateTimeFormat('en-US', { timeZone: s.timezone, ...opts }).format(new Date(ms));
const today = fmt(now, { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/(\d+)\/(\d+)\/(\d+)/, '$3-$1-$2');

// ---- minimal PDF writer --------------------------------------------------------------
const ASCII = { '‘': "'", '’': "'", '“': '"', '”': '"', '–': '-', '—': '-', '…': '...' };
const pdfText = (v) => String(v == null ? '' : v)
  .replace(/[‘’“”–—…]/g, (c) => ASCII[c])
  .replace(/[^\x20-\x7E\xA0-\xFF]/g, '?')
  .replace(/[\\()]/g, (c) => '\\' + c);
const clip = (v, n) => { const t = String(v == null ? '' : v); return t.length > n ? t.slice(0, n - 3) + '...' : t; };

function makePdf(pages) {
  // pages: array of content-stream strings. Objects: 1 catalog, 2 pages, 3 Helvetica,
  // 4 Helvetica-Bold, then a page object and a content stream per page.
  const objs = [];
  const kids = pages.map((_, i) => `${5 + i * 2} 0 R`).join(' ');
  objs.push('<< /Type /Catalog /Pages 2 0 R >>');
  objs.push(`<< /Type /Pages /Kids [${kids}] /Count ${pages.length} >>`);
  objs.push('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>');
  objs.push('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>');
  pages.forEach((content, i) => {
    objs.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${6 + i * 2} 0 R >>`);
    objs.push(`<< /Length ${content.length} >>\nstream\n${content}\nendstream`);
  });
  let out = '%PDF-1.4\n%\xE2\xE3\xCF\xD3\n';
  const offsets = objs.map((o, i) => { const at = out.length; out += `${i + 1} 0 obj\n${o}\nendobj\n`; return at; });
  const xref = out.length;
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  out += offsets.map((o) => `${String(o).padStart(10, '0')} 00000 n \n`).join('');
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(out, 'latin1'); // every character above is a single byte
}

const text = (x, y, size, str, bold) => `BT /${bold ? 'F2' : 'F1'} ${size} Tf ${x} ${y} Td (${pdfText(str)}) Tj ET\n`;
const rule = (y) => `0.8 G 0.5 w 50 ${y} m 562 ${y} l S\n`;
// Breaks text into lines of at most `width` characters (Helvetica 10pt fits ~95 across the page).
const wrap = (v, width) => String(v || '').trim().split(/\s+/).filter(Boolean).reduce((lines, word) => {
  const last = lines[lines.length - 1];
  if (last !== undefined && (last + ' ' + word).length <= width) lines[lines.length - 1] = last + ' ' + word;
  else lines.push(word);
  return lines;
}, []);
const COLS = [[50, 'Date', 22], [180, 'Time', 40]];

function schedulePdf(c, appts) {
  const pages = [];
  let page = '';
  let y = 0;
  const header = (first) => {
    y = 742;
    if (first) {
      page += text(50, y, 18, 'Upcoming appointments', true); y -= 22;
      page += text(50, y, 11, s.practiceName); y -= 16;
      page += text(50, y, 11, `Patient: ${c.name}`); y -= 16;
      page += text(50, y, 9, `Prepared ${fmt(now, { month: 'long', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}`); y -= 28;
    }
    COLS.forEach(([x, label]) => { page += text(x, y, 10, label, true); });
    y -= 6; page += rule(y); y -= 16;
  };
  header(true);
  for (const a of appts) {
    if (y < 90) { pages.push(page); page = ''; header(false); }
    const time = fmt(a.StartDate, { hour: 'numeric', minute: '2-digit' });
    const cells = [
      fmt(a.StartDate, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }),
      time + (a.Status === 'WaitingConfirmation' ? ' (pending confirmation)' : ''),
    ];
    COLS.forEach(([x, , n], i) => { page += text(x, y, 10, clip(cells[i], n)); });
    y -= 6; page += rule(y); y -= 16;
  }
  y -= 10;
  if (y < 60) { pages.push(page); page = ''; y = 742; }
  page += text(50, y, 10, `${appts.length} upcoming appointment${appts.length === 1 ? '' : 's'}. If anything looks wrong, please call us at ${s.practicePhone}.`);
  const policy = wrap(s.cancellationPolicy, 95);
  if (policy.length) {
    y -= 28;
    if (y - 14 * policy.length < 50) { pages.push(page); page = ''; y = 742; }
    page += text(50, y, 11, 'Cancellation policy', true); y -= 16;
    for (const line of policy) { page += text(50, y, 10, line); y -= 14; }
  }
  pages.push(page);
  return makePdf(pages);
}

// ---- one PDF per due client ----------------------------------------------------------
const out = [];
for (const c of due) {
  // The PracticeQ "client" filter is a partial name/email match, so keep only this client's rows.
  const seen = new Set();
  const appts = rows
    .filter((r) => String(r.ClientId) === String(c.clientId) && OPEN.includes(r.Status) && Number(r.StartDate) > now)
    .filter((r) => !seen.has(r.Id) && seen.add(r.Id))
    .sort((a, b) => a.StartDate - b.StartDate);
  if (!appts.length) continue; // everything was cancelled during the wait

  const live = isLive(c);
  const uploadTo = live ? c.clientId : s.testClientId;
  if (!uploadTo) continue;
  // Earlier summaries for the same patient share the prefix and are replaced after upload.
  const filePrefix = `${live ? '' : `TEST - ${String(c.name).replace(/[\\/:*?"<>|]/g, '')} - `}Upcoming appointments `;
  const fileName = `${filePrefix}${today}.pdf`;
  out.push({
    json: { ...c, uploadTo, count: appts.length, fileName, filePrefix },
    binary: { data: { data: schedulePdf(c, appts).toString('base64'), mimeType: 'application/pdf', fileName, fileExtension: 'pdf' } },
  });
}
return out;
