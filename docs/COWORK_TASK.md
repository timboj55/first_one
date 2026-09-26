# Cowork task: finish the IntakeQ ledger setup (browser steps)

Paste everything below this line into a Cowork session in the Claude desktop app.

---

You are completing browser-based setup steps for an IntakeQ package-ledger automation. Work in my
browser. Rules: never type, paste or read out any API key, token or password into chat, into a
file, or into any field other than the exact destination named below. Do not activate any n8n
workflow. Do not change the PracticeQ webhook URL. When a step needs a decision I have not made,
stop and ask me. At the end, report only the non-secret facts listed in step 6.

## 1. Claude Code cloud environment (claude.ai/code)
Open claude.ai/code, find the environment named "Default" (cloud environment menu or settings),
click Edit.
- Network access: add the allowed domain `n8n.movementsolutions-sc.com`. Keep the existing
  `intakeq.com` and `support.intakeq.com` entries.
- Environment variables (NOT the API credentials section): make sure these exist, exact names:
  - `INTAKEQ_API_KEY`  = the PracticeQ Developer API key (copy it from step 2, paste only here)
  - `N8N_BASE_URL`     = `https://n8n.movementsolutions-sc.com`
  - `N8N_API_KEY`      = the n8n public API key (create it in step 3, paste only here)
- Save the environment. Confirm the three variable names are listed after saving.

## 2. PracticeQ
Log in to PracticeQ. Go to More > Settings > Integrations > Developer API (Settings button).
- Confirm "Enable API access" is checked.
- Confirm no IP allow-list is set (or note that one is, and which IPs).
- Copy the API key with the copy button and paste it ONLY into the `INTAKEQ_API_KEY` field in
  step 1. Do not display it in chat.
- Note the rate limit shown in "Select Maximum Requests".

## 3. n8n (https://n8n.movementsolutions-sc.com)
- Settings > n8n API: create an API key labelled "claude-code-ledger". Paste it ONLY into the
  `N8N_API_KEY` field in step 1.
- Credentials > Add credential > "Header Auth": name it exactly `IntakeQ API (X-Auth-Key)`,
  header Name `X-Auth-Key`, Value = the PracticeQ API key (from step 2, paste only here). Save.
- Help / About (or Settings): record the n8n version.
- In a new blank workflow, use the node search to check whether these nodes exist, then discard
  the workflow without saving: "Execute Command", "Data Table" (or "Data Tables"),
  "Read/Write Files from Disk".
- Settings > Environments or the admin panel if present: note whether the container has a
  persistent files folder (commonly `/home/node/.n8n-files`). Skip if not visible.

## 4. Cockpit repository access
In claude.ai/code repository settings (or Settings > Connectors > GitHub), make the cockpit
repository (the one containing `data/packages_all.csv` and `data/appt_packages.json`) available
to Claude Code. Record its `owner/name`.

## 5. Where the 4:06am refresh runs
Open the cockpit repository on GitHub. Check `.github/workflows/` for a scheduled workflow, and
check n8n for a workflow scheduled around 04:06 America/New_York. Record which one exists.

## 6. Report back (non-secret facts only)
- Environment "Default" saved with the three variable names present: yes/no
- Allowed domain added: yes/no
- PracticeQ: Enable API access checked; IP allow-list state; rate limit shown
- n8n version; which of the three nodes exist; persistent files folder path if seen
- Header Auth credential `IntakeQ API (X-Auth-Key)` created: yes/no
- Cockpit repo `owner/name` and whether it is now available to Claude Code
- Where the 4:06am refresh runs
