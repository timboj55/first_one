// Code node "Build emails" (run once for all items).
// Input: every appointment from today on for each due client (from "Get upcoming").
// Output: one item per email to send, with the GHL recipient, subject and HTML body.
const s = $('Settings').first().json;
const due = $('Queue bookings').all().map((i) => i.json);
const rows = $input.all().map((i) => i.json).filter((r) => r && r.Id);
const OPEN = ['Confirmed', 'WaitingConfirmation'];
const now = Date.now();
const live = s.mode === 'live';

const esc = (v) => String(v == null ? '' : v)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const fmt = (ms, opts) => new Intl.DateTimeFormat('en-US', { timeZone: s.timezone, ...opts }).format(new Date(ms));

const out = [];
for (const c of due) {
  // The PracticeQ "client" filter is a partial name/email match, so keep only this client's rows.
  const seen = new Set();
  const appts = rows
    .filter((r) => String(r.ClientId) === String(c.clientId) && OPEN.includes(r.Status) && Number(r.StartDate) > now)
    .filter((r) => !seen.has(r.Id) && seen.add(r.Id))
    .sort((a, b) => a.StartDate - b.StartDate);
  if (!c.email || !appts.length) continue; // nothing to send (no email on file, or all cancelled)

  const to = live ? c.email : s.testEmail;
  if (!to) continue;

  const first = esc(String(c.name).trim().split(/\s+/)[0] || 'there');
  const lines = appts.slice(0, 40).map((a) => `
    <tr>
      <td style="padding:8px 12px;border-bottom:1px solid #eee;white-space:nowrap">${fmt(a.StartDate, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</td>
      <td style="padding:8px 12px;border-bottom:1px solid #eee;white-space:nowrap">${fmt(a.StartDate, { hour: 'numeric', minute: '2-digit' })}</td>
      <td style="padding:8px 12px;border-bottom:1px solid #eee">${esc(a.ServiceName)}${a.Status === 'WaitingConfirmation' ? ' <em>(awaiting confirmation)</em>' : ''}</td>
      <td style="padding:8px 12px;border-bottom:1px solid #eee">${esc(a.PractitionerName)}</td>
      <td style="padding:8px 12px;border-bottom:1px solid #eee">${esc(a.LocationName)}</td>
    </tr>`).join('');
  const more = appts.length > 40 ? `<p>…and ${appts.length - 40} more.</p>` : '';

  const html = `<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#222;line-height:1.5">
  <p>Hi ${first},</p>
  <p>Here ${appts.length === 1 ? 'is your upcoming appointment' : `are your ${appts.length} upcoming appointments`} with ${esc(s.practiceName)}:</p>
  <table style="border-collapse:collapse;font-size:14px">
    <tr style="text-align:left;background:#f5f5f5">
      <th style="padding:8px 12px">Date</th><th style="padding:8px 12px">Time</th><th style="padding:8px 12px">Visit</th><th style="padding:8px 12px">With</th><th style="padding:8px 12px">Location</th>
    </tr>${lines}
  </table>${more}
  <p>If anything looks wrong or you need to make a change, please call us at ${esc(s.practicePhone)} or reply to this email.</p>
  <p>See you soon,<br>${esc(s.practiceName)}</p>
</div>`;

  const subject = `Your upcoming appointments at ${s.practiceName}`;
  out.push({
    json: {
      ...c,
      to,
      count: appts.length,
      subject: live ? subject : `[TEST for ${c.name} <${c.email}>] ${subject}`,
      html,
    },
  });
}
return out;
