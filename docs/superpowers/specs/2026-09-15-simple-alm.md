# Simple Power Platform ALM — design for review

Status: analysis and proposed design, 2026-09-15. No tenant resources have been inspected or changed. The workspace was empty when planning began. Implementation requires the user's answers and acceptance of the proposed scope below.

## Confirmed requirements

- Use three existing developer environments: ADMIN, DEV, TEST.
- SharePoint is the application data source. Dataverse supports solutions.
- First build three SharePoint sites and an unmanaged DEV solution named Demo, with a new publisher named dev.
- ADMIN SharePoint: configuration list, versioned solution archive library, logs/results library.
- DEV SharePoint: simple Products list. TEST SharePoint: initially empty of custom content.
- Demo: a read-only canvas app displaying Products, environment-based SharePoint binding, and a flow retrieving the first product and composing it.
- Design the ADMIN deployment application after this foundation is working.
- Later ADMIN UI: show configuration, select a solution, start deployment, display progress and results.
- Later deployment: export DEV, archive an unmanaged ZIP in ADMIN SharePoint, import to TEST, and apply TEST bindings. First deployment must work when TEST has no Demo solution or dev publisher.
- Implement using sub-agents. Build only the confirmed stable core.
- Confirmed 2026-09-15: use the Microsoft Dataverse connector for runtime solution export/import from ADMIN. User requested plan update and compaction preparation before implementation continues with sub-agents. This confirms the connector choice, not the unanswered setup decisions below.

## Environment map

| Role | Dataverse URL | Proposed SharePoint URL |
|---|---|---|
| ADMIN | https://adminorg774eae27.crm17.dynamics.com | https://7xpydh.sharepoint.com/sites/ALM-Admin |
| DEV | https://devorgf20ef6ea.crm17.dynamics.com | https://7xpydh.sharepoint.com/sites/ALM-Dev |
| TEST | https://testorg5fd244de.crm17.dynamics.com | https://7xpydh.sharepoint.com/sites/ALM-Test |

Environment GUIDs, tenant identity, site availability, permissions, connections, DLP policy and usable licenses remain unverified. URL hostnames are not environment GUIDs.

## Decisions requiring answers

**Accepted 2026-09-16:** user selected “Use all proposed defaults” for all six decisions below. Owner/account: kriall076@7xpydh.onmicrosoft.com (confirmed Chrome identity). The numbered proposals below now form the accepted foundation contract: managed TEST, two variables, group-free team sites, dev prefix/Demo 1.0.0.0, corrected config column, separate TEST preparation.

1. Managed or unmanaged Demo in TEST? Recommend managed; always archive unmanaged from DEV.
2. Accept two data-source environment variables, Site and List? Microsoft documents both as required for SharePoint canvas app data sources. Exactly one URL variable would require revisiting the direct SharePoint app design; do not silently substitute a flow-backed app.
3. Confirm site paths above and the owner account. Proposed sites are private team sites without Microsoft 365 groups, subject to tenant support and user acceptance.
4. Confirm publisher unique name/display name `dev` and customization prefix `dev`. Proposed solution unique/display name `Demo`, initial version `1.0.0.0`.
5. Confirm the five config columns below. The request repeats Test Power Platform URL; the proposed correction is Dev SharePoint URL.
6. Before the first deployment, should a separate setup task create TEST Products, or should the deployment worker create it? Recommend separate setup for this first demo. TEST remains empty through the foundation phase either way.

## Proposed foundation contract

### ADMIN SharePoint

`ALMConfig`: one row per solution and DEV→TEST route. Built-in ID identifies the configuration; Title can remain optional/hidden. Use the solution unique name for export, never resolve a display name ambiguously.

| Internal name | Type | Demo value |
|---|---|---|
| SolutionName | Single line of text; required | Demo |
| DevPowerPlatformUrl | Hyperlink; required | DEV Dataverse URL above |
| TestPowerPlatformUrl | Hyperlink; required | TEST Dataverse URL above |
| DevSharePointUrl | Hyperlink; required | Approved DEV site URL |
| TestSharePointUrl | Hyperlink; required | Approved TEST site URL |

`Solutions`: document library with major version history. Archive path `Solutions/Demo/solution.zip`; replace file content on each successful export to create a new SharePoint version. Preserve previous versions. This supplies a versioned ZIP archive; it does not provide text diffs or branching. No Git-based ALM service is included.

`DeploymentLogs`: document library for run records and import result files. Initially create the library only. Phase 2 can add run metadata described below after design acceptance.

### DEV SharePoint

`Products`: standard custom list. Keep the built-in `Title` text field as product name and built-in `ID` as the deterministic ordering key. Seed three rows: `DEV - Apple`, `DEV - Banana`, `DEV - Coffee`. No prices, categories, inventory or edit UI.

### DEV Demo solution

| Component | Proposed name | Behavior |
|---|---|---|
| Publisher | dev, prefix dev | Own all Demo custom components |
| Solution | Demo | Unmanaged, version 1.0.0.0 |
| Site variable | dev_SharePointSite | Data source / SharePoint / Site; DEV site current value |
| List variable | dev_ProductsList | Data source / SharePoint / List; bound to Site variable; DEV list identifier current value |
| Connection reference | dev_SharePoint | Valid DEV SharePoint connection used by solution flow |
| Canvas app | Demo Products | One gallery displaying product Title |
| Flow | Demo - Get First Product | Manual trigger → Get items → empty check → Compose |

Select existing Site and List variables in the canvas app's SharePoint Advanced connection picker. A text URL variable read in an app formula is not equivalent to data-source rebinding. Verify the actual canvas connector dependencies in the exported solution; do not assume its connection behavior is identical to the flow's connection reference.

Flow Get items uses both variables, Order By `ID asc`, Top Count `1`. If no rows exist, Compose receives null; otherwise it receives the first complete product object. App and flow need not call each other: the request only requires two dummy consumers of the same data source.

Export environment-variable definitions without DEV current values included in the transport package; leave working DEV values in DEV. No DEV URL default that could silently become a TEST fallback. Target connections must already exist and be usable by the importing identity. Solution packages move connection references, not credentials.

## Later ADMIN ALM design — proposal, not authorized implementation

Use a separate ADMIN solution (proposed name `ALMAdmin`) for the management app and flows. Demo stays the application under deployment. Confirm this container name/publisher during Phase 2 design.

The connector choice is confirmed: use Microsoft Dataverse **Perform an unbound action in selected environment** for solution operations. Set Environment dynamically to the validated DEV or TEST base URL from ALMConfig. Use an approved owner/service identity connection with permissions in both organizations; cross-environment instant flows cannot use a Dataverse connection set to Provided by run-only user. The connector is premium; verify applicable developer/test entitlements and DLP during preflight.

Use `ExportSolutionAsync` with `SolutionName` and `Managed`, poll its `AsyncOperationId`, and retrieve the ZIP with `DownloadSolutionExportData` using `ExportJobId`. Import using `ImportSolutionAsync`, supplying target environment-variable and connection-reference overrides through `ComponentParameters`; preserve its `AsyncOperationId` and `ImportJobKey`. Validate the precise connector payload and binary handling in task 7. Use selected-environment row reads for job status and validation.

PAC CLI is optional local authoring/export tooling, not a dependency of the ADMIN runtime. Power Apps for Admins and Power Platform for Admins (including V2) have no solution ZIP export/import actions in the reviewed catalog. Add an admin connector only for a specific required ownership/connection lookup if one is identified.

Proposed minimal runtime: two flows and the existing logs library.

1. `ALM - Request Deployment`, Power Apps (V2): accept ConfigId and client-generated RequestId, validate the configured DEV/TEST route, write a run JSON file, return RunId promptly. Reject unsupported routes; the app cannot supply arbitrary target URLs. Reuse a matching RequestId if a response was lost.
2. `ALM - Deploy`, triggered when a run file is created: execute one deployment at a time, update its library metadata with the current stage, and store the result. Exclude result attachments and folders from the trigger so log creation does not recurse.
3. ADMIN app: show ALMConfig, select one solution per run, invoke request flow, then refresh the matching log metadata every five seconds while running. Display stages and results; no fabricated percentage. Support reopening a run by its ID.

Run file metadata proposal: RunId (text, unique), ConfigId (number), SolutionName (text), State (choice), Stage (text), StartedUtc and CompletedUtc (date/time), ResultSummary (multiline), ArtifactUrl (hyperlink). State values: Queued, Running, Succeeded, Failed, NeedsAttention. JSON content captures the configuration snapshot, job IDs, solution version, archive version identifier and errors. Logs contain no tokens or credentials.

Worker stages:

1. Validate DEV solution/publisher, TEST target type, TEST Products schema and connection mappings. Missing target solution/publisher is allowed. A conflicting publisher or managed/unmanaged type is a failure requiring intervention.
2. Ensure TEST Products exists according to decision 6. SharePoint lists and data are outside the solution package. Compare source/target column internal names and metadata; identical visible column names alone are insufficient. Keep TEST product data distinct from DEV.
3. Export unmanaged from DEV; poll the export job, download it, and save a new `Solutions/Demo/solution.zip` version. Record that precise archive version in this run. If archiving fails, stop before import.
4. If managed TEST is chosen, export a managed package from the same published DEV version. Do not attempt to convert an unmanaged ZIP by renaming/editing it. Prevent authoring changes between these paired exports and verify matching solution versions.
5. Import asynchronously to TEST with TEST Site/List values and the TEST SharePoint connection reference mapping. Import creates the solution/publisher when absent. Do not pre-create an empty unmanaged Demo in TEST.
6. Poll actual import status. Preserve job IDs and the formatted result. Treat elapsed polling deadline as NeedsAttention if the server job may still be running; do not automatically resubmit an uncertain import.
7. Verify target solution version, bindings and flow readiness. Confirm app/flow read TEST sentinel data in the end-to-end acceptance test. Only then mark the demonstrated deployment successful.

Connection IDs and environment-variable schema names require a deployment mapping. For this Demo-only core, store a mapping JSON in the existing ADMIN config item's attachment rather than adding another configuration subsystem. Confirm its shape during Phase 2; discover TEST Products ID by approved site/list name and verify metadata. Credentials are never stored in SharePoint configuration.

A connector feasibility check must prove the required export/import action parameters, binary transfer, connection mapping and variable overrides from ADMIN. If the selected-environment connector cannot serialize the documented parameters, report that result and propose the smallest supported API option before changing architecture.

## Execution skills and tooling — updated 2026-09-16

Use [ability discovery and readiness](../../alm/abilities.md) as the skill-routing contract. Skill files are installed; live MCP readiness is a separate gate. Preserve the full Microsoft bundle at `.tooling/power-platform-skills-a804d33267c973314e21f56827e0743ee3f1e690`; resolve `${PLUGIN_ROOT}` to its `plugins/canvas-apps` or `plugins/power-automate` directory in each task brief. Do not resolve it to the flattened installed skill directory.

| Work | Required workflow |
|---|---|
| Identity/auth preflight | Existing dv-connect, explicit target checks; approved Chrome session is available. No unrelated profile changes or new tenant permissions. |
| SharePoint sites/lists/libraries | Supported SharePoint admin/browser workflow with Microsoft Docs; no exact site-provisioning skill found in the narrowed repositories. |
| Publisher/solution and export verification | Existing dv-solution, verified API signatures via Microsoft Code Reference. PAC is local tooling only; ADMIN runtime stays Dataverse connector. |
| Canvas authoring | Installed configure-canvas-mcp + canvas-app; live Studio session, sync before edits, describe controls, compile and playback. Use full bundle references and planner/builder briefs with Codex sub-agents. One simple gallery only. |
| Canvas data-source binding | Studio Advanced Site/List environment-variable selection; Canvas MCP does not add data sources. Browser workflow remains available; if the selected add-data-source skill requires maker intervention, disclose the exact requirement before pausing. |
| Flow authoring and tests | Installed power-automate-setup, build-flow, manage-flows. Discover actual connector operations, validate/preflight, create stopped, verify solution membership/connection references/variables, then publish and run authorized tests. Never accept placeholders as finished. |

Project `.codex/config.toml` contains Canvas Authoring and FlowAgent stdio entries. No live tools are currently exposed; reload/startup and authenticated smoke checks are required before using MCP workflows. FlowAgent also needs Azure CLI authentication, absent at preflight; Chrome cookies are not an Azure CLI token source. Canvas needs an actual app/Studio coauthoring session, which foundation has not created yet. Continue supported browser foundation work while these gates are resolved.

Keep domain authorship tools distinct from the solution's runtime architecture. Installing skills does not add product features, approve cloud permissions, or replace first-import proof. Sub-agents must receive exact environment IDs, assigned files, relevant skill paths, and exclusive tenant mutation ownership. Map upstream Claude-specific tool/model names to available Codex tools; never claim unavailable MCP tools ran.

## Boundaries

- Foundation ends with DEV Demo working and TEST still empty of custom content; cross-environment rebinding cannot yet be claimed proven.
- Phase 2 starts with a real TEST binding/import rehearsal, then finalizes the ADMIN design.
- No rollback automation, production deployment, approval workflows, schedules, bulk parallel deployment, generic SharePoint schema migration, solution deletion or inventory features.
- No tenant-wide security changes, additional cloud services, custom connectors or dependency installation without a concrete need and applicable authorization.
- Existing developer environments are for this development/test exercise. Preflight verifies account entitlements and connector/DLP compatibility; this plan makes no production licensing claim.

## Source findings

- [SharePoint Site and List variables and matching metadata](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/environmentvariables#how-do-environment-variables-work).
- [Canvas app connection procedure](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/environmentvariables-data-source-canvas-apps).
- [Power Apps for Admins supported actions](https://learn.microsoft.com/en-us/connectors/powerappsforadmins/).
- [Dataverse selected-environment actions](https://learn.microsoft.com/en-us/connectors/commondataserviceforapps/).
- [Dynamic environment URLs, connection identities and limitations](https://learn.microsoft.com/en-us/power-automate/dataverse/connect-to-other-environments).
- [Power Platform for Admins V2 action catalog](https://learn.microsoft.com/en-us/connectors/powerplatformadminv2/).
- [Asynchronous solution operations and component parameters](https://learn.microsoft.com/en-us/power-platform/alm/solution-async).
- [Connection reference validation during automated deployment](https://learn.microsoft.com/en-us/power-platform/alm/conn-ref-env-variables-build-tools).
- [Managed/unmanaged solution concepts](https://learn.microsoft.com/en-us/power-platform/alm/solution-concepts-alm).
- [Caller timeout and asynchronous flow pattern](https://learn.microsoft.com/en-us/power-automate/guidance/coding-guidelines/asychronous-flow-pattern). The HTTP example does not itself prove Power Apps (V2) behavior; the proposed queued-worker approach avoids relying on that assumption.

## Knowledge-hub discovery

### Current-work summary

Searched for a Microsoft repository example of SharePoint-backed canvas/flow solution ALM driven by an ADMIN environment. Discovery only; no assets were installed or executed.

### Relevant examples

No directly matching indexed example was found in this bounded search. Current Microsoft Learn solution-operation documentation supplies the architectural grounding instead.

### No-match or exclusions

Power Pages ALM material targets a different application runtime. Canvas and FlowAgent pages found in the examples lanes are authoring/validation guidance, not end-to-end ALM examples.

### Confirm before adapting

Verify the documented Dataverse import/export parameter shapes against the available connector designer and tenant before authoring deployment flows.

### Discovery trace

- Wiki ID: power-platform.
- Workload domains: canvas-apps, power-automate; examples lanes.
- Concept pages: canvas-apps/examples/sources-and-validation.md; power-automate/examples/references-and-operation-safety.md.
- Fallback: knowledge-index/assets.json, narrowed to Power Platform-related sources, ALM/export/import/deployment and example/demo/sample/lab roles; no match.
- Exact sources opened under `C:/Users/KristofferAllåker/Development/Work/Internal/power-platform-skill/`: WIKI_INDEX.md; catalogues/power-platform.md; openwiki/domains/index.md; each named workload index and examples/index.md; both concept pages above; knowledge-index/assets.json.
- Material uncertainty: search is bounded, not a claim that Microsoft has no such example anywhere. No candidate example was recommended, so source-entry adaptation was unnecessary.
