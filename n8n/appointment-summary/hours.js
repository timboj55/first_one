// Code node "Business hours?" (run once for all items). Sweeper branch.
// Lets the run continue only during business hours plus `afterCloseMinutes` after closing,
// in the practice's time zone, and never on a listed holiday. Outside that window nothing is
// processed; queued patients wait for the next opening.
const s = $('Settings').first().json;
const hours = JSON.parse(s.businessHours);
const holidays = String(s.holidays || '').split(',').map((d) => d.trim()).filter(Boolean);

const parts = Object.fromEntries(
  new Intl.DateTimeFormat('en-US', {
    timeZone: s.timezone, weekday: 'short', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(Date.now())).map((p) => [p.type, p.value]),
);
const day = parts.weekday.toLowerCase().slice(0, 3);
const date = `${parts.year}-${parts.month}-${parts.day}`;
const minute = Number(parts.hour) * 60 + Number(parts.minute);
const toMinute = (hhmm) => { const [h, m] = hhmm.split(':').map(Number); return h * 60 + m; };

const span = hours[day];
const open = Array.isArray(span) && !holidays.includes(date)
  && minute >= toMinute(span[0]) && minute < toMinute(span[1]) + Number(s.afterCloseMinutes || 0);
return open ? [{ json: { open: true, day, date } }] : [];
