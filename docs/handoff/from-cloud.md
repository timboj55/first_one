# From the cloud session

## 2026-09-30

### Status
- Verified IntakeQ's public API against the official docs and recorded it in README.md. No
  packages endpoint; package fields only on GET /appointments/{id}; AppointmentPackageId is
  the package type, not the purchase (your live measurement, now in README).
- Retired the ledger/nightly/webhook/n8n drafts (last at commit db839bf). Kept a read-only
  client and a `verify` command in `intakeq_packages/`.
- Wrote the IntakeQ support request (`docs/intakeq-support-request.md`). Tim is sending it.
- Wrote the provisional-purchases bridge spec (`docs/provisional-purchases-spec.md`). Tim
  approved the idea; implementation is yours, dry run first.
- Recommended removing the INTAKEQ_API_KEY and N8N_API_KEY credentials from the Claude Code
  "Default" environment and deleting the unused n8n Header Auth credential
  "IntakeQ API (X-Auth-Key)". Tim is doing this via Cowork.
- Your session pushed nothing here yet; the lead-agent commit on this branch came from a
  separate iOS session.

### Decisions needed from Tim
- None open on my side beyond the ones above.

### Questions for the cockpit session
1. Does the spec in `docs/provisional-purchases-spec.md` fit how merge_packages.py and the
   ledger build are structured? Name anything that should change before you implement.
2. Which package names in the last 90 days of invoice line items do NOT match the eleven
   names in the spec (distinct description strings only)? That tells us whether the matcher
   needs aliases.
3. Is there anything you want from this session: API details, docs lookups, or a second pair
   of eyes on a diff? The IntakeQ docs host is reachable from here.
