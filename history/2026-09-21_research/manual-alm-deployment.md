# Manual ALM deployment with SharePoint release storage

Use unmanaged solutions in Dev and managed solutions in Test and Prod. Managed solutions do not require Managed Environments; these are separate concepts.

1. Build and check in Dev. Save and publish the intended app/solution changes. Run solution checker and a basic functional check.
2. Freeze the release briefly, assign a solution version, and export both unmanaged and managed ZIPs from that same Dev state. Do not edit between the two exports. Store them in a new SharePoint release folder; never overwrite a released ZIP.
3. Prepare Test SharePoint schema/permissions and target connections. Import the managed ZIP, set target site/list variables and bind connection references. Verify actual data-source targets and flow activation/ownership.
4. Test with representative user permissions and service-account flow connections. Record business-owner approval against the exact package/version. If it fails, fix in Dev, create a new version and retest.
5. Prepare Prod prerequisites, then import the same approved managed ZIP from the release folder. Do not re-export from Test or rebuild from changed Dev contents. Use the intended update/upgrade mode consistently in Test and Prod; component removals require upgrade planning.
6. Smoke-test the app and flows, verify SharePoint targets, and record deployed version, date, operator and result.

Suggested folder:

```text
ALM-Releases/<SolutionName>/1.2.0.0/
  <SolutionName>_1_2_0_0_unmanaged.zip
  <SolutionName>_1_2_0_0_managed.zip
  release-notes.md
  deployment-record.md
  target-settings.md
  sharepoint-changes.md
```

Enable library version history and restrict release-package editing. Release files remain unchanged; the deployment record can accumulate Test approval and Prod results. Keep passwords/tokens out of target settings. SharePoint storage is a temporary release archive, not a replacement for Git diffs, branches or merging. Dev remains the working authoring environment.

SharePoint sites, list schemas, permissions and business data are outside the Power Platform solution package. Track schema changes as release steps, ideally repeatable scripts later. Apply compatible schema changes before the importing app/flow needs them; plan removals separately. Use separate Dev/Test/Prod data targets.

For a failed release, record a recovery plan before deployment. Prefer a corrected higher-version release through the same path. An older ZIP is not a guaranteed one-click rollback, and solution imports do not restore SharePoint data.

Sources checked 2026-09-21:

- [Microsoft: solution concepts](https://learn.microsoft.com/en-us/power-platform/alm/solution-concepts-alm)
- [Microsoft: import solutions](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/import-update-export-solutions)
- [Microsoft: connection references and environment variables in deployment settings](https://learn.microsoft.com/en-us/power-platform/alm/conn-ref-env-variables-build-tools)
- [Microsoft: data source environment variables for canvas apps](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/environmentvariables-data-source-canvas-apps)
