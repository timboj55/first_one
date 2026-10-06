// Code node "Check lookups" (run once for all items). Runs after the PDF branch has finished.
// Input: everything "Get upcoming" returned (one empty item when PracticeQ returned nothing).
// A due patient for whom PracticeQ returned no appointment rows at all, not even cancelled
// ones, was not found by the lookup (usually a missing or changed email), so no PDF was filed.
// That fails the run, which sends the workflow's error alert. A patient whose appointments
// were all cancelled still has rows and is correctly skipped without an error.
const due = $('Keep due').all().map((i) => i.json);
const found = new Set($input.all().map((i) => i.json).filter((r) => r && r.Id).map((r) => String(r.ClientId)));

const missing = due.filter((c) => !found.has(String(c.clientId)));
if (missing.length) {
  const who = missing.map((c) => `client ${c.clientId} (${c.name || 'no name'}${c.email ? '' : ', no email on file'})`).join('; ');
  throw new Error(`No PDF filed: PracticeQ returned no appointments for ${who}. Check the patient's email in PracticeQ, then rebook or ask Claude to re-queue them.`);
}
return [];
