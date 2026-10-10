# Training doc updates

Scripts for applying `training_doc_update_for_claude_code.md` (in Google Drive) to
"Tray Training Plan: Your Map" (doc ID `1bnACsOdoc9obw_dsOX9Z8zj8SrMvwX2dv_9E7Z7LzWE`).

- `spec.py` - find/replace items (Round 1B and 2E) with expected match counts.
- `outline.py doc.json` - headings, tables, and inline images with indices.
- `dryrun.py doc.json <dir of spec.py>` - counts each Find in the doc; flags mismatches or already-done items.
- `anchors.py doc.json` - checks insert anchors and records checkbox and Date-cell baselines.

Get `doc.json` with
`curl -sS "https://docs.googleapis.com/v1/documents/<DOC_ID>?includeTabsContent=true" -o doc.json`.

Status (2026-10-10): backup made ("Tray Training Plan BACKUP before update 2026-10-08").
Dry run clean: all 26 finds match expected counts, none already done. Baseline: 58 checked,
68 unchecked, 54 filled Date cells. 1E skipped (Gmail row Who cell already "CC").
No edits applied yet: the environment's Google credential is read-only scoped.
