# DemoDeployPipeline alignment review

Reviewed 2026-09-22 against commit `5c2199dcff9ad2d4781445745b35b32594a8d3e4` of [DemoDeployPipeline](https://github.com/kristoffer-a/DemoDeployPipeline/tree/5c2199dcff9ad2d4781445745b35b32594a8d3e4).

## Verdict and scope

The design is substantially aligned with our solution model and is a useful foundation for custom ALM without hosted Git or Managed Environments. The repository documents a partial implementation, not a demonstrated deployment pipeline. The material differences are the environment topology, retention of the managed release artifact, and absence of production promotion/approval.

This is a static review of repository files and recorded evidence, not a live tenant audit. Historical instructions to resume implementation in the repository were treated as review material; no tenant calls, authentication changes, imports or deployments were performed. The latest handoff takes precedence over earlier inventory/progress records. The repository contains documentation, draft flow inputs and authoring helpers; there is no exported solution package in the reviewed tree to inspect independently.

Our reference model: three customer environments (Dev, Test, Prod); Dataverse metadata is acceptable; SharePoint stores business data and temporary release archives; unmanaged authoring in Dev; managed deployment to Test and Prod; limited licensed service identities; separate application and SharePoint permission assignments.

## What aligns

| Area | Assessment | Repository evidence |
|---|---|---|
| Business data vs metadata | Correctly distinguishes SharePoint application data from Dataverse solution infrastructure. | [Spec lines 7–17](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/superpowers/specs/2026-09-15-simple-alm.md#L7-L17) |
| Solution packaging | Unmanaged Demo in Dev; managed Test accepted. App, two data-source variables and a connection reference are recorded inside Demo; the flow is intended to join it. | [Handoff lines 21–43](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/alm/HANDOFF.md#L21-L43) |
| Canvas data-source binding | Uses the actual SharePoint Site and List variables through Studio Advanced pickers, rather than merely substituting a URL in a formula. Recorded published playback reads Dev data. | [App evidence](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/alm/demo-app.md#L20-L47) |
| Configuration transport | Excludes Dev current values/default fallbacks from the package; target connections exist separately; credentials are not transported. | [Spec lines 74–78](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/superpowers/specs/2026-09-15-simple-alm.md#L74-L78) |
| SharePoint prerequisites | Explicitly recognizes schema and data are outside the package and requires separate Test preparation and distinct sentinel data. | [Spec lines 100–106](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/superpowers/specs/2026-09-15-simple-alm.md#L100-L106) |
| Separate deployment capability | Proposed ALMAdmin solution is separate from the Demo business solution. This fits one solution per independent business capability. | [Spec line 82](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/superpowers/specs/2026-09-15-simple-alm.md#L82) |
| Runtime orchestration design | Short request flow plus asynchronous worker; route validation, request IDs, serialized deployment, job polling, actual result verification and NeedsAttention for uncertain timeouts. These are good planned controls, not implemented proof. | [Spec lines 84–110](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/superpowers/specs/2026-09-15-simple-alm.md#L84-L110) |

## Findings, in priority order

### 1. The checked-in checkpoint has not yet proved deployment

The September 20 handoff records no saved cloud flow, a pending connection-reference rebind, no foundation export/inspection, no first Test import/rebinding rehearsal and no implemented deployment worker/UI. Four-component Dev membership and a working gallery are good evidence for the foundation only. [Handoff lines 13–17 and 37–49](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/alm/HANDOFF.md#L13-L49)

Do not present this snapshot as a working end-to-end deployment pipeline. The next proof should be: complete the flow, inspect an actual export, import managed into Test, demonstrate both app and flow reading Test-only records while Dev remains unchanged, then repeat an update. This is missing milestone evidence, not evidence that the proposed architecture cannot work.

### 2. Archive the managed artifact as well as the unmanaged snapshot

The spec deliberately overwrites `Solutions/Demo/solution.zip` while preserving SharePoint versions and records the precise archive version. That is a defensible temporary source archive; it is not inherently wrong. However, worker stages explicitly archive only the unmanaged export, then separately export managed for Test. They do not explicitly retain that managed ZIP for later production promotion. [Spec line 54 and lines 102–104](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/superpowers/specs/2026-09-15-simple-alm.md#L54)

For our current stance, use a release folder such as `Solutions/Demo/1.2.0.0/` containing both ZIPs plus release metadata. Keep those ZIPs unchanged and associate Test approval with the exact managed file (optionally record SHA-256). Prod consumes that file from storage; it must not trigger a fresh export from a now-changed Dev solution. Keep SharePoint version history as an additional safeguard. A fixed-path design could also work with explicit artifact-version IDs and retention controls, but version-specific folders are easier to operate manually.

The spec already requires a freeze between paired exports; preserve that. Matching version strings alone are not proof of identical content if makers can still edit.

### 3. ADMIN / DEV / TEST does not fit the customer's DEV / TEST / PROD allocation

The demo's three environments are all developer environments and include a separate Admin host; Prod is absent. Adding Prod without changing that topology requires a fourth environment. This is a deliberate demo scope difference, not an error in its original contract. [Spec environment map](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/superpowers/specs/2026-09-15-simple-alm.md#L19-L27), [inventory](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/alm/environment-inventory.json)

For the customer, retain Dev/Test/Prod and start with the manual process we documented. A SharePoint Admin site/library does not require a fourth Power Platform environment. If the custom deployment UI/worker is retained later, choose an existing environment to host the separate ALMAdmin solution and explicitly control who can edit it and use its production deployment connection. Merely placing ALMAdmin in a separate solution does not create a security boundary. Do not copy the demo's developer-environment types as the customer production topology.

### 4. Add a release-promotion operation, not just another export-and-import route

The original scope explicitly excludes production deployment and approvals. Config currently describes Dev→Test, and the proposed worker begins by exporting Dev. [Spec lines 44–52 and 129–135](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/superpowers/specs/2026-09-15-simple-alm.md#L129-L135)

Extend the conceptual process into two operations:
- Create release: freeze Dev, export both packages, archive them, deploy managed to Test.
- Promote release: select an existing successful Test release, verify recorded business approval, deploy its stored managed ZIP to Prod and record the result.

Record release ID/version, artifact identity, target, approver, operator, import job/result and smoke-test result. The approval can initially be manual and recorded in SharePoint. Automated approvals are not required to meet the current stance.

### 5. The saved draft flow inputs are not portable

`task-5-create-args.json` hardcodes the Dev site/list in Get_items and the old connection ID in connectionRefs. The handoff correctly warns that these are unfinished draft inputs and must not be submitted unchanged. [Draft lines 35–36 and 75–82](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/alm/task-5-create-args.json#L35-L36), [handoff line 47](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/alm/HANDOFF.md#L47)

A flow exported with those literal data targets could still read Dev after import, despite environment variables existing elsewhere in the solution. Complete the rebind, use the intended Site/List variable references, verify solution membership, and inspect the exported package. The currently recorded missing connection is missing for the new operating identity; the evidence does not prove it is universally deleted.

### 6. Security and the service-account access path remain separate acceptance work

SharePoint foundation evidence records an owner and no member/visitor groups. App playback was done as the creator. This does not demonstrate Entra group-based app access, ordinary users' SharePoint permissions, or access denied when expected. [Foundation line 22](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/alm/sharepoint-foundation.md#L22), [app validation](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/alm/demo-app.md#L34-L43)

The dummy flow deliberately has a manual trigger and is independent of the app. That is enough for testing two consumers' bindings once implemented, but it does not demonstrate our diagram's explicit app→flow→service-account path. [Flow intent](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/alm/demo-flow.md#L13-L22)

When bringing the demo up to the current illustration, add a small ordinary-user test and, if that route is intended for the customer, a Power Apps-triggered flow test. Keep application user access distinct from permission to request deployments. Restrict who can modify ALM route configuration and create worker-triggering request files; tool-side authoring identity guards do not establish runtime authorization.

### 7. Dataverse remains a dependency, including a premium deployment connector

The design explicitly uses the Dataverse selected-environment connector for async solution operations. This fits our clarified requirement of no business data in Dataverse, but should not be described as zero Dataverse or standard-connectors-only. The spec already flags premium licensing and DLP/permission verification. [Spec lines 84–88](https://github.com/kristoffer-a/DemoDeployPipeline/blob/5c2199dcff9ad2d4781445745b35b32594a8d3e4/docs/superpowers/specs/2026-09-15-simple-alm.md#L84-L88)

Do not infer customer production licensing from a working developer demo. The feasibility check should establish actual connector payloads, selected-environment rights, connection use and applicable licensing. Managed solutions are distinct from Managed Environments; our manual/custom import route need not adopt native Power Platform pipelines.

## Recommended next step

Keep the existing component/binding design. First prove a single managed Dev→Test release, including actual export contents, data separation and repeat import. Before adding an Admin UI, adopt a stable release record storing both packages and manual Test approval. Then extend to Prod by consuming the same tested package. Automate that proven process later if the operation volume justifies the custom worker.

The deployment solution can manage other solutions without the business applications taking component dependencies on it. Keep each business solution's custom components self-contained; environment connections, SharePoint data and identity permissions remain explicitly external dependencies.

## Platform references

- [Microsoft: solution concepts](https://learn.microsoft.com/en-us/power-platform/alm/solution-concepts-alm)
- [Microsoft: asynchronous solution operations](https://learn.microsoft.com/en-us/power-platform/alm/solution-async)
- [Microsoft: connect to other Dataverse environments](https://learn.microsoft.com/en-us/power-automate/dataverse/connect-to-other-environments)
- [Microsoft: data-source variables in canvas apps](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/environmentvariables-data-source-canvas-apps)
- [Microsoft: Dataverse connector](https://learn.microsoft.com/en-us/connectors/commondataserviceforapps/)
- Supplemental current-source checks: [platform guidance](demo-deploy-platform-guidance.md).

No repository or tenant implementation was changed by this review.

