# Support request to IntakeQ / PracticeQ: packages in the Developer API

Send from the account owner's login via the in-app support chat or hello@intakeq.com. Plain
text below; replace the bracketed items.

---

Subject: Developer API: request for appointment-package (purchase) data

Hello,

We are a PracticeQ customer ([practice name], account owner [name], API enabled on our account,
20 requests/minute tier). We automate our reporting through the Developer API and one piece of
data still requires a manual export: appointment packages.

What we can get today
- GET /appointments/{id} returns AppointmentPackageId and AppointmentPackageName, but the id
  identifies the package type, not the client's purchase, so usage cannot be attributed to a
  purchase through the API.
- GET /invoices shows package sales as line items, but without the sessions sold or any usage
  counters.
- The list endpoint GET /appointments does not include the package fields at all.

What we need, which currently exists only in the Bookings > Packages export
- A read-only endpoint returning client package purchases, for example GET /clientPackages
  with the same filters as other list endpoints (clientId, startDate, endDate, updatedSince,
  page), returning per purchase: Id, ClientId, PackageId, PackageName, DateCreated, Status,
  Paid, InvoiceNumbers, TotalSessions, UsedSessions, UnusedSessions, ExpiryDate, Practitioner.
- Ideally, the purchase Id (ClientPackageId) on the appointment object returned by
  GET /appointments/{id}, and the package fields on the GET /appointments list as well.
- Optionally, a webhook event when a client package is created, updated or cancelled.

Why
Our package export is capped at 2,000 rows and must be downloaded and merged by hand. Our
nightly reporting depends on PracticeQ's own UsedSessions/UnusedSessions counters, which we
do not want to re-derive. An endpoint would let us retire the manual export entirely.

Is anything like this on the roadmap, and can the request be logged with your product team?
If a beta exists, we are happy to test it.

Thank you,
[name], [practice], [account email]
