# Task 1 — bounded local/API preflight

Read-only tenant task. Inspect existing PAC authentication and available local tooling; never print tokens or credential-file contents. No installs, auth creation/select/switch, tenant writes, browser use, or sub-agents. Controller handles browser separately.

URLs: ADMIN https://adminorg774eae27.crm17.dynamics.com; DEV https://devorgf20ef6ea.crm17.dynamics.com; TEST https://testorg5fd244de.crm17.dynamics.com. SharePoint root https://7xpydh.sharepoint.com/.

PAC exists at C:/Users/KristofferAllåker/.dotnet/tools/pac.exe. No Git repo. Read relevant dv-solution and, if needed, dv-connect skill before tooling. Use help to verify commands. Inspect existing authenticated profiles safely, and if supported explicit environment targeting can read identities, publishers, solutions and connections without shared profile mutation, do so. Do not fetch token files or display tokens. Check installed SharePoint modules/CLI availability without installation. Unknown permissions/licensing/DLP remain unknown; command availability does not prove access.

Own docs/alm/environment-inventory.json and docs/alm/task-1-preflight-report.md only. Inventory environments entries: role, url, environmentId, organizationId, verifiedAccount (null when unknown), evidence/status. sharePoint approved URLs and owner null pending user; proposed paths ALM-Admin, ALM-Dev, ALM-Test must be explicitly marked unapproved. tooling includes versions and check outcomes. Report exact blockers and next account action, safe command evidence, no secrets. Task is partial unless identities and permissions verified; do not claim acceptance. Return concise status and report path.
