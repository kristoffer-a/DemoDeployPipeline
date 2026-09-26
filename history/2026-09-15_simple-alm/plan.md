# Simple Power Platform ALM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking. Read the spec and this plan; user instructions take precedence over skill defaults.

**Goal:** Build the three SharePoint sites and working DEV Demo foundation, then use that evidence to design and implement the separately accepted ADMIN deployment core.

**Architecture:** SharePoint holds configuration, products, solution archives and deployment results. DEV Demo contains a canvas app, flow, connection reference and SharePoint data-source variables. The later ADMIN app delegates long-running solution operations to flows using Dataverse.

**Tech Stack:** SharePoint Online, Power Apps canvas, solution-aware Power Automate, Dataverse solutions, authenticated maker/admin tooling; PAC CLI only where available and validated.

**Spec:** [Design and decisions](../specs/2026-09-15-simple-alm.md).

**Resume after compaction:** Read [handoff](../../alm/HANDOFF.md) and [progress](../../alm/progress.md) first. As of 2026-09-15 only planning is complete; no implementation task has started.

## Global constraints

- 2026-09-16 execution update: all six proposed foundation defaults accepted, including owner kriall076@7xpydh.onmicrosoft.com. Follow spec's Execution skills and tooling section and docs/alm/abilities.md. Skills installed does not imply MCP authenticated/loaded.

- Build only the confirmed stable core. No tenant mutations during this planning turn.
- User confirmed Microsoft Dataverse as the deployment connector on 2026-09-15. ADMIN runtime uses selected-environment actions, with dynamic validated DEV/TEST base URLs from ALMConfig; no PAC CLI runtime dependency.
- Resolve spec decisions 1–6 before dependent implementation; unanswered recommendations are not accepted features.
- ADMIN: https://adminorg774eae27.crm17.dynamics.com.
- DEV: https://devorgf20ef6ea.crm17.dynamics.com.
- TEST: https://testorg5fd244de.crm17.dynamics.com.
- SharePoint root: https://7xpydh.sharepoint.com/.
- DEV solution display name Demo; new publisher name dev. Other proposed names require acceptance.
- TEST site initially empty of custom lists/data; do not create Products during foundation.
- Never change/delete unrelated existing resources. Reuse an exact matching resource on rerun; stop on an incompatible collision.
- Record IDs, names, environment and verification evidence after each task. Never record tokens.
- Shared tenant/browser/PAC authentication state is not isolated by git worktrees. Only one agent may mutate it at a time.

## File structure and ownership

All paths are relative to the workspace root. These files are execution deliverables, not an instruction to create scaffolding now.

| File/directory | Responsibility | Owning task |
|---|---|---|
| docs/alm/environment-inventory.json | Confirmed environment/site identities and tool readiness | 1 |
| docs/alm/progress.md | Task state, approved decisions and evidence links | Controller |
| docs/alm/sharepoint-foundation.md | Actual list/library IDs, schema and provisioning record | 2 |
| docs/alm/demo-components.json | DEV publisher, solution, variable and connection-reference IDs | 3 |
| docs/alm/demo-app.md | App ID, data-source bindings and playback evidence | 4 |
| docs/alm/demo-flow.md | Flow ID, action configuration and run evidence | 5 |
| artifacts/Demo/ | Exported baseline ZIP, created only during execution | 6 |
| docs/alm/foundation-acceptance.md | Foundation checks and remaining TEST binding proof | 6 |
| docs/alm/test-binding-proof.md | Real first-import/rebinding results | 7 |
| docs/superpowers/plans/2026-09-15-admin-deployment.md | Phase 2 executable plan based on feasibility results | 7 |

Prefer supported Studio/designer creation over inventing app packages or hand-editing undocumented formats. Export captures the actual built artifacts. If scripts become useful for repeatability, agree on them within the implementation task; they are not required extra deliverables.

## Sub-agent execution method

Controller owns accepted scope, decisions, ledger and exclusive tenant-write access. Dispatch a fresh bounded implementer for each task with only its task, relevant spec sections and prior task outputs. Use a task reviewer for spec compliance and quality after each deliverable, followed by one final integration review. Resume the same implementer for corrections.

Execute tenant mutation tasks sequentially. Read-only review can overlap independent local documentation work. Do not launch multiple browser editors or switch shared authentication profiles concurrently. No persistent new Codex tasks are required.

At execution time inspect whether a Git repository exists. If present, follow the worktree skill for local isolation. If absent, use the current workspace and file ownership; do not invent a Git repository or remote as a product requirement. Local Git isolation never substitutes for tenant coordination.

## Phase 1 — foundation

### Task 1: Verify identities, access and approved contract

**Agent:** environment-preflight. **Files:** create docs/alm/environment-inventory.json.

**Consumes:** user answers, environment URLs in spec. **Produces:** JSON with `environments` entries containing role, url, environmentId, organizationId and verifiedAccount; `sharePoint` containing approved site URLs and owner; `tooling` containing available tool versions and access-check outcomes. Unknown IDs are not guessed.

- [ ] Record accepted decisions in docs/alm/progress.md, including site type, publisher prefix and TEST package type.
- [ ] Inspect available authenticated tools. Read the connection skill if authentication setup is needed. Verify the signed-in identity and organization separately for ADMIN, DEV and TEST, using explicit target URLs.
- [ ] Read existing solution/publisher names in DEV and TEST and check proposed SharePoint site paths for collisions.
- [ ] Verify site creation rights, SharePoint data access and Dataverse customization rights. Check connector/DLP and development/test entitlements for SharePoint and Dataverse actions.
- [ ] Verify an approved Dataverse connection identity can perform selected-environment operations in DEV and TEST. Use an owner/service identity connection for the ADMIN runtime, not Provided by run-only user for cross-environment instant flows. Record identity and connection IDs without credentials.
- [ ] Save the inventory without credentials. If authentication or permissions are missing, name the exact account action required; do not provision under an arbitrary identity.

**Acceptance:** three distinct verified organizations map to the supplied URLs; site ownership and every required design choice are recorded. This task is read-only against tenant resources.

### Task 2: Provision the SharePoint foundation

**Agent:** sharepoint-foundation. **Files:** create docs/alm/sharepoint-foundation.md.

**Consumes:** verified inventory and approved SharePoint contract. **Produces:** three site IDs/URLs; ADMIN ALMConfig, Solutions, DeploymentLogs IDs; DEV Products ID and field metadata.

- [ ] Create the approved ADMIN, DEV and TEST sites with the approved owner. Reuse exact matches found during preflight.
- [ ] Create ALMConfig and its five fields with the internal names/types in the spec. Add exactly one Demo configuration row with the approved URLs.
- [ ] Create Solutions and enable major version history. Create DeploymentLogs. Record actual library settings.
- [ ] Create DEV Products using only built-in ID and Title, and seed the three specified DEV records once.
- [ ] Verify stored URLs, config field types, list internal names and seeded records by reading them back.
- [ ] Verify TEST contains no custom Products list or demo data. Record all resource IDs and source field metadata.

**Acceptance:** configuration is readable, both libraries exist, Solutions versioning is enabled, DEV Products contains the three seed records, TEST remains empty of custom content. Rerun creates no duplicates.

### Task 3: Create Demo publisher, solution and binding components

**Agent:** demo-solution. **Files:** create docs/alm/demo-components.json.

**Consumes:** inventory and DEV Products/site IDs. **Produces:** exact publisher ID, solution ID/unique name, environment-variable schema names/IDs, connection-reference logical name/ID and DEV connection ID.

- [ ] In verified DEV, create publisher dev with the accepted prefix, or reuse an exact compatible pre-existing match. Do not select a default publisher.
- [ ] Create unmanaged Demo version 1.0.0.0 with that publisher.
- [ ] Create the accepted Site and List data-source variables inside Demo. Use the real DEV site and list current values and bind the List parameter to the Site variable.
- [ ] Create a SharePoint connection reference inside Demo and bind it to the approved DEV connection.
- [ ] Read back solution membership, variable metadata/current values and connection-reference status. Save the exact identities for downstream agents.

**Acceptance:** correct publisher and unmanaged solution; expected components belong to Demo; variable values resolve to DEV Products. Do not create TEST solution/publisher.

### Task 4: Build the read-only Demo canvas app

**Agent:** demo-canvas. **Files:** create docs/alm/demo-app.md.

**Consumes:** task 3 component identities. **Produces:** published app ID and verified SharePoint binding evidence.

- [ ] Create Demo Products from inside Demo in DEV.
- [ ] Add the SharePoint Products data source using Advanced selection of the existing Site and List environment variables.
- [ ] Add one gallery; set Items to `Products` and its label Text to `ThisItem.Title`. Use the actual Studio data-source identifier if Studio names it differently and record that identifier.
- [ ] Save, run App checker, resolve data/formula errors and publish.
- [ ] Play the published app as the approved account. Verify all three DEV product names render. Record app ID and binding evidence.

**Acceptance:** actual published canvas app displays DEV list data with environment-variable bindings. No editing screens or unrelated UI features.

### Task 5: Build the dummy first-product flow

**Agent:** demo-flow. **Files:** create docs/alm/demo-flow.md.

**Consumes:** task 3 binding identities. **Produces:** solution flow ID and successful run evidence.

- [ ] Create Demo - Get First Product inside Demo using a manual trigger.
- [ ] Add SharePoint Get items with action name `Get_items`, Site and List from the existing variables, Order By `ID asc`, Top Count `1`, using the solution connection reference.
- [ ] Add a condition `empty(body('Get_items')?['value'])`. On true, Compose the expression `null`; on false, Compose `first(body('Get_items')?['value'])`. This avoids calling first on an empty array.
- [ ] Save and run. Verify the composed ID equals the smallest DEV Products ID and Title equals the matching product.
- [ ] Exercise the empty branch with a temporary nonmatching filter on the demo flow, then remove that filter and rerun the restored final flow. Record both outcomes and the final configuration.

**Acceptance:** nonempty result is deterministic; empty result is null without failure; final flow remains unfiltered and uses the same Site/List variables as the app.

### Task 6: Verify and export the foundation

**Agent:** foundation-validation. **Files:** create artifacts/Demo/Demo_1.0.0.0_unmanaged.zip and docs/alm/foundation-acceptance.md.

**Consumes:** tasks 1–5 evidence. **Produces:** verified DEV baseline and explicit Phase 1 sign-off evidence.

- [ ] Inspect Demo solution membership: app, flow, both approved variable definitions, required connection reference/dependencies. Remove nothing outside Demo.
- [ ] Exclude DEV environment-variable current values from export while keeping DEV runtime values working; inspect the resulting archive to confirm no transported DEV binding defaults/current values.
- [ ] Export unmanaged Demo with explicit DEV targeting using supported tooling. Record solution version and export time; inspect the ZIP manifest and component contents.
- [ ] Reopen the published DEV app and run the final DEV flow. Verify both still read DEV Products after export configuration changes.
- [ ] Verify the three sites, five config fields, archive versioning setting and empty TEST condition from task 2. Record each check as pass/fail with evidence.
- [ ] Obtain independent review of spec coverage and tenant identities. Report foundation completion only when these checks pass.

**Acceptance:** usable unmanaged Demo export and working DEV dummy components. TEST rebinding remains explicitly untested. The local artifact verifies exportability; automatic ADMIN archive storage belongs to the later deployment worker.

## Phase 2 entry — only after foundation and design acceptance

### Task 7: Prove TEST rebinding and finalize deployment implementation

**Agent:** deployment-feasibility. **Files:** create docs/alm/test-binding-proof.md and docs/superpowers/plans/2026-09-15-admin-deployment.md.

**Consumes:** accepted TEST package/provisioning decisions and foundation artifacts. **Produces:** real binding evidence and a fully specified ADMIN implementation plan. Do not implement the ADMIN UI before this evidence exists.

- [ ] Apply the agreed TEST list preparation path. Use source-compatible field metadata; seed `TEST - Tea` for verification without copying DEV product data.
- [ ] Create/verify an approved TEST SharePoint connection and record its ID. Confirm the importing identity can use it.
- [ ] From ADMIN, use Microsoft Dataverse Perform an unbound action in selected environment with DEV URL from configuration. Call ExportSolutionAsync with SolutionName and Managed, poll AsyncOperationId to successful completion, then call DownloadSolutionExportData with ExportJobId. Verify the downloaded ZIP can be stored and read back through SharePoint without corrupting binary/base64 content.
- [ ] Use the same connector with the TEST URL and ImportSolutionAsync. Prove the actual connector payload accepts ComponentParameters for target Site/List variable values and connection-reference mapping. Record the exact working payload shape and returned AsyncOperationId/ImportJobKey. Ground parameter names in current Microsoft documentation and connector metadata; user acceptance of this connector does not substitute for this integration check.
- [ ] Import the approved package type into TEST with Site/List and connection mappings. Verify solution/publisher creation on the first import, and capture actual job status/result.
- [ ] Open the imported published app and run the TEST dummy flow; both must show/compose TEST - Tea while DEV still shows DEV data. Verify effective variable values and no DEV binding fallback.
- [ ] Finalize the ADMIN contract in a second executable plan: accepted solution/publisher names, request and worker flows, config attachment mapping, log metadata, run trigger filtering, app formulas, action parameter shapes, timeouts and acceptance checks.

**Acceptance:** first import/rebinding works; the ADMIN runtime design is concrete and accepted before implementation. A feasibility failure is reported with exact evidence and the smallest supported alternative, without silently adding services.

### Subsequent sub-agent tasks in that second plan

| Order | Agent | Deliverable and verification |
|---|---|---|
| 8 | admin-request | ADMIN solution/container, approved log metadata and request flow; returns the same RunId for a retried RequestId and rejects invalid configuration before queuing |
| 9 | deployment-worker | Validates target, archives unmanaged, exports managed if selected, imports with bindings, tracks job results; first and repeat deployment tests pass |
| 10 | admin-canvas | Configuration gallery, one-solution selection, deployment trigger and run status/result view; stays responsive during long imports |
| 11 | integration-review | Verify DEV/TEST data separation, archive history/version linkage, repeat deployment without duplicates, invalid connection/schema failure before import, and timeout state without duplicate imports |

The second plan must specify actual flow/connector inputs from task 7. This table is a roadmap, not permission to implement unconfirmed Phase 2 details.

## Plan review record

- Coverage: sites/config/libraries/DEV data → task 2; publisher/solution/bindings → task 3; app → task 4; dummy flow → task 5; foundation verification → task 6; cross-environment proof and later ALM design → task 7.
- Shared interfaces: task 1 inventory → all tasks; task 2 resource IDs → task 3; task 3 binding IDs → tasks 4/5; tasks 4/5 artifacts → task 6; task 6 baseline → task 7. Each producer and consumer is named above.
- Phase boundary preserves the user's requirement that TEST starts empty and the actual deployment solution is designed after the foundation.
- No live integration checks have been executed during planning. Connector feasibility, identity and permission claims remain unverified until their named tasks.
