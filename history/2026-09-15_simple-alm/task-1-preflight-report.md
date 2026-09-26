# Task 1 — local/API preflight report

Date: 2026-09-15
Result: **Partial — browser discovery succeeded; authenticated local/API verification did not.**

The controller verified all three target environments and SharePoint in the existing browser session. See [browser-preflight.md](browser-preflight.md). This establishes the environment URLs and IDs, Ready state, Developer type, Switzerland region, Dataverse availability, and version `9.2.26085.142`. It does not establish Dataverse user identity, roles, connector ownership, or write permission.

The machine has PAC CLI `2.10.1+g52c3983`. Its help confirms that `pac org who`, `pac solution list`, `pac connection list`, and `pac env fetch` all support explicit `--environment` targeting. The explicit ADMIN identity check reached authentication but failed with `AADSTS70043`: the cached refresh token had expired under the seven-day sign-in-frequency policy. The three stored PAC profiles point to unrelated CRM4 environments; none targets ADMIN, DEV, or TEST. Dataverse CLI `1.0.72` is installed but has no authentication profiles.

Because identity verification failed, publisher, solution, and connection inventories were not queried. Retrying those calls would produce no stronger evidence until authentication is repaired. No active PAC profile was selected or changed, no authentication was created, and no tenant resource was mutated.

## Exact blockers and next account action

1. **Local Dataverse authentication:** Sign in PAC with the approved Axfood account for each target URL, expected to be `kriall076@7xpydh.onmicrosoft.com` only if the user confirms that account. Then run the explicit URL checks below. Browser access remains available, so this blocks API-based verification rather than all implementation paths.
2. **Dataverse authorization:** Customization rights, solution/publisher access, connection visibility, connector ownership, licensing, and DLP remain unknown until authenticated checks succeed.
3. **SharePoint ownership and permission:** The site owner is still `null` pending the user's choice. The browser displayed the Create command, but a read-only visit does not prove site creation permission.
4. **SharePoint URL reservations:** Active-sites search for `ALM-` returned zero results. Deleted sites were not checked, so deleted-site URL reservations remain unknown. The proposed paths `/sites/ALM-Admin`, `/sites/ALM-Dev`, and `/sites/ALM-Test` are unapproved.
5. **Local SharePoint tooling:** CLI for Microsoft 365, PnP.PowerShell, and SharePoint Online Management Shell are not installed. This does not prove or disprove tenant access.

## Safe command evidence

After authentication is intentionally established, these read-only commands keep target selection explicit:

```powershell
pac org who --environment <target-url>
pac solution list --environment <target-url>
pac connection list --environment <target-url>
pac env fetch --environment <target-url> --xml "<fetch><entity name='publisher'><attribute name='publisherid'/><attribute name='uniquename'/><attribute name='friendlyname'/><attribute name='customizationprefix'/></entity></fetch>"
```

Run them for ADMIN, DEV, and TEST and confirm the returned account and organization IDs against [environment-inventory.json](environment-inventory.json). Do not treat command availability as evidence of account permission.

## Local tooling snapshot

| Tool | Result |
|---|---|
| PAC CLI | `2.10.1+g52c3983`, installed at the brief's supplied path |
| Dataverse CLI | `1.0.72`, installed; no auth profiles |
| Python | `3.12.10` |
| Git | `2.53.0.windows.3`; this workspace is not a Git repository |
| Node.js | `25.9.0` |
| .NET SDK | `10.0.204` |
| Azure CLI | Not installed |
| SharePoint CLI/modules | No supported local administration CLI/module found |

Task 1 does not meet acceptance yet: identities and permissions are unverified. The durable structured snapshot is [environment-inventory.json](environment-inventory.json).
