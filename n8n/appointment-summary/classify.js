// Code node "Classify event" (run once for all items). Webhook branch.
// Input: a PracticeQ appointment event forwarded by the "IntakeQ Appointments -> GHL"
// workflow. Output: one queue row for the "booking_summary_queue" data table.
//
// Every appointment event is queued, so later changes (another booking, a reschedule, a
// cancellation) push a waiting patient's PDF back. Only a new, open, future appointment
// (`isBooking`) makes a PDF happen at all; the sweeper drops patients with no booking row.
const OPEN = ['Confirmed', 'WaitingConfirmation'];
const now = Date.now();

return $input.all().flatMap(({ json }) => {
  const e = json.body && typeof json.body === 'object' ? json.body : json;
  const a = e.Appointment || {};
  const clientId = a.ClientId || e.ClientId;
  if (!clientId) return [];
  return [{
    json: {
      clientId: String(clientId),
      clientName: a.ClientName || '',
      clientEmail: a.ClientEmail || '',
      eventAt: now,
      isBooking: e.EventType === 'AppointmentCreated' && OPEN.includes(a.Status) && Number(a.StartDate) > now,
      attempts: 0,
    },
  }];
});
