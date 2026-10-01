# Platform Operations integration

Updated 2026-10-01. Working branch: `codex/flowadmin-deployment-contract`, based on ALM commit `4883edd`. This record separates observed state, local changes and proposed rollout. The candidate is deployed only to dedicated TEST qualification resources. October 1 also provisioned TEST Products and fixed its mapping/current value. ADMIN Demo imports are disabled; the setup helper was restored and parent/child definitions remain unchanged. No business records were copied. Diagrams are excluded from the current scope.

## Decision and ownership

Combine ALM-af and FlowError as one Platform Operations product while retaining four deployable solutions. Preserve existing solution names, publisher prefixes and source histories. Establish deployment contracts before moving repositories, SharePoint sites or live solutions.

| Module | Existing solution | Owns |
| --- | --- | --- |
| Core | FlowAdminCore | Environment registry, shared settings definitions and foundational provisioning |
| ALM | ALMPipeline | Release artifacts, desired deployment configuration, orchestration and deployment history |
| Monitoring | FlowAdminMonitoring | Collectors, cursors, incident lifecycle, recovery and operational notifications |
| Governance | FlowAdminGovernance | Observed inventory, ownership, policy findings and change history |

Core must not depend on higher modules. Monitoring must continue without successful governance refreshes; ALM retains its own failure logs without monitoring. Share references only where identity, permissions and lifecycle match. Keep deployment privileges separate from collector permissions.

Platform lifecycle: unmanaged DEV → managed TEST → operational ADMIN. Business solutions follow DEV → TEST → PROD. TEST platform configuration must use isolated lists, notification destinations and monitored scope. Existing unmanaged ADMIN solutions need a rehearsed migration, not an assumed managed import conversion. Keep an independent bootstrap/recovery path for ALMPipeline.

Initially retain FlowError's existing SharePoint location and ALM-Admin. Eventually consider a Platform Operations data domain. Use stable environment IDs for identity, with stage labels as attributes. Keep desired configuration, observed state and historical evidence separate. Business application data remains in business domains.

## Baseline evidence

| Observation | Evidence and confidence |
| --- | --- |
| Approved Azure context | Read-only `az account show`: tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`, approved kriall076 account |
| Dataverse scanner Started | Flow API read on 2026-09-30, workflow `8b436393-4cbc-f111-aaaf-000d3a832204` |
| Legacy scanner Stopped | Flow API read on 2026-09-30, workflow `74d00317-46b1-f111-aaab-002248db522e` |
| Recent scanner runs succeeded | Runs `08584108683058881134486337818CU31` (03:22 UTC) and `08584108701061047619197909060CU02` (02:52 UTC), September 30 |
| ALM C1/C2/C3 Started; setup helper Stopped | Read-only Flow API inventory, September 30; definitions last modified September 24 |
| FlowError replay changes remain local | Linked chat “Analyze solution and ALM-af setup” latest completed turn and active feature-worktree handoff; not redeployed by this work |
| Scanner state manifest is stale | Feature-worktree `_workflow-ids.json` lists the legacy scanner on and Dataverse scanner off, opposite to live reads |
| TEST connection mapping | Fresh SharePoint UI read September 30: `dev_SharePoint` → `shared-sharepointonl-0f567e53`; old wrong-mapping warning is resolved. Connection authentication itself was not retested |
| TEST variables | Fresh UI read: site URL is ALM-Test; `dev_ProductsList` remains `00000000-0000-0000-0000-000000000000` and blocks a working Demo app |
| ALMConfig | Fresh UI read: RunImport Yes, RunPostImport Yes, RunShare No; legacy TestPowerPlatformUrl/TestSharePointUrl columns still exist. No cleanup performed |

Successful scheduled runs do not prove coverage, notification retries or replay correctness. Do not use the stale manifest as desired deployment state. FlowError worktree:
`/Users/kristoffer/.codex/worktrees/dataverse-failurescan-review/FlowError`.

ALM's existing `DemoDeployPipeline-sharepoint-work` worktree is preserved; its SharePoint deployment work is still a proposal. FlowError's main checkout and feature worktree were inspected, not modified.

## Implemented locally

- Versioned activation JSON schema and flowless Demo example.
- C1 manifest validation, forwarding, sidecar archive and log evidence.
- C2 independent manifest validation and source/target cloud-flow inventory gate.
- C3 full manifest coverage validation before variable/state writes, disabled-first reconciliation, ordered enabling and final readback. Failed state writes leave a marker that blocks subsequent loop iterations.
- Configuration-only C1 runs validate against the target inventory and skip export/archive entirely; import/export-only runs validate against DEV. Reconciliation evidence is recorded in the deployment log.
- Fail-closed inventory limits, including FetchXML paging indications.
- Approved-account allowlist before token acquisition, in addition to the tenant guard.
- Deployment lookup scoped to ALMPipeline and definition-type cloud flows, rejecting duplicates; updates carry the owning-solution header.
- Candidate generation stays in a temporary directory until deployment succeeds, preserving historical definition snapshots if authentication fails.
- Regression tests against generated actions and simulated inventory.
- Actual managed ZIP inspection and a versioned hash descriptor bind solution identity/version, exact bytes, activation policy and cloud-flow IDs. C1 verifies before archiving; C2 independently re-verifies the archived pair before import. Unconfigured verification fails closed.
- Local authenticated verifier service and an offline exact-byte release runner. The user explicitly chose local service preparation and disabled one-click imports until hosting is approved. Hash descriptors require trusted separate protection; they are not signatures.
- Explicit isolated-target profiles, dedicated connection references, paused-parent/quiescence checks, children-first rollout and version updates. Live ADMIN deployment is blocked by the candidate CLI.
- Inert qualification fixtures and dedicated SharePoint bootstrap source; no production notification or business-data actions.
- Local CI workflow covering tests, definition generation and authentication-policy checks.

The [contract](../../contracts/README.md) documents inputs and exact limitations. This is an ADMIN-undeployed candidate with selected isolated TEST paths qualified, not a completed FlowAdmin deployment route. The deployed JSON snapshots in `pipeline/definitions/` intentionally remain unchanged.

## Remaining rollout gates

1. **Verifier hosting deferred by user:** package inspection and hash binding are implemented and tested locally. Keep one-click imports disabled. Before enabling them, provision approved HTTPS hosting, authentication at runtime, trusted descriptor storage and run end-to-end archive/import acceptance. See [local verifier](artifact-verifier.md).
2. **Import activation qualification:** demonstrate when cloud flows start on fresh import and update, with enabled/disabled exported states and bound connections. `PublishWorkflows` is not a cloud-flow switch. Choose a packaging/staging procedure that establishes prerequisites before any runtime activity.
3. **Isolated runtime verification:** deploy the candidate into an isolated test harness, not over the live ADMIN parent/children. Confirm actual Parse JSON schema support, child input binding, state transitions, log/sidecar fields and failure behavior. The deployment tooling now accepts an explicit isolated target and rejects live ADMIN use; actual runtime evidence remains required.
4. **ALM baseline:** TEST Products is provisioned, its schema verified and mapping/current value corrected. Fresh target-user app access still requires browser sign-in. Account and solution-lookup fixes were used for isolated qualification; ADMIN engine source is not replaced. Legacy Test* columns remain; deletion is not needed for activation work.
5. **FlowError source readiness:** local main is clean at `08798c7`; definitions/exports and desired metadata are reconciled. Controlled replay, retry, same-flow recovery and heartbeat checks are recorded in its acceptance document. Fresh 48 tests and 15 static checks pass. Large connector load and non-Dataverse Poll coverage remain operational limits; no push has occurred.
6. **Provisioning/dependencies:** idempotent external schema migrations, per-environment current values and connection bindings, then Core before dependent modules. Verify the existing Core reference migration in actual packages.
7. **Release lifecycle:** parent/child rollout, explicit versions, exact-byte release runner and bootstrap source are prepared locally. Exercise recovery, trusted artifact promotion and remote CI before source merge. No commits, pushes or PRs have been made in this implementation turn.

## TEST acceptance procedure

Use inert test flows with no production notification destination or production data access. Record their stable workflow IDs and complete manifest. Start with one disabled helper, one enabled legacy fixture, and a stopped child/parent pair intended to start.

1. Missing, malformed, duplicate, foreign and incomplete manifests must fail with no variable or flow-state writes.
2. Declare legacy/helper off and child/parent on, child first. Verify legacy stops before any enable; child starts before parent; helper remains off.
3. Repeat unchanged manifest: no unnecessary restarts. Inject an enable or disable failure and verify subsequent iterations perform no state writes and later phases do not report success. Inspect partial state explicitly.
4. Verify the final readback fails if a concurrent change or simulated write discrepancy leaves a wrong state. Concurrency exclusion remains an operator prerequisite until a deployment lock exists.
5. Prove the import inventory gate for source-only and target-only flows, direct C2 invocation and C1's RunImport switch. Package inspection is implemented locally; verify the hosted path before enabling imports.
6. With an extra unreleased flow in DEV, verify a configuration-only C1 run accepts the complete target manifest. Verify missing/invalid manifests return structured child failure and C1 records failure even if import/post-import is skipped.
7. Confirm the ZIP and activation sidecar are associated correctly, and a failed sidecar write prevents import.
8. Record runtime duration against the synchronous child limit. The 100-entry schema limit is not proof of acceptable runtime. Use an asynchronous job contract if measured execution can exceed that limit.

After these gates: prove fresh Core + Monitoring installation and upgrade in TEST; only then consolidate repository histories and plan ADMIN migration. Governance can follow independently after Core. Shared administration UI comes after the module contracts stabilize.

## Validation record

- October 1 local tests and selected TEST runtime checks: see [qualification evidence](qualification-2026-10-01.md).
- Candidate C1/C2/C3 generated successfully with `python3 -m pipeline.deploy --dry-run`.
- Definition-validator check: final C1/C2/C3 candidate returned `valid: true` after the paging-check extension.
- No live ZIP imports, commits or pushes. Isolated qualification resources were deployed; TEST Products mapping/current value were fixed; ADMIN Demo RunImport is false and C2 is stopped; setup source/state restored.
- Diagram validation above belongs to the September 30 candidate. Diagrams were excluded from October 1 implementation and were not edited or revalidated.

## References

- [Flow activation contract](../../contracts/README.md)
- [Current handoff](HANDOFF.md)
- [Runbook](deploy-orchestrator-runbook.md)
- [Microsoft cloud-flow identifiers and import parameters](https://learn.microsoft.com/en-us/power-automate/manage-flows-with-code)
- [Microsoft import state behavior](https://learn.microsoft.com/en-us/power-automate/import-flow-solution)
- [Current connection mappings](https://7xpydh.sharepoint.com/sites/ALM-Admin/Lists/ALMConnections/AllItems.aspx)
- [Current variable mappings](https://7xpydh.sharepoint.com/sites/ALM-Admin/Lists/ALMVariables/AllItems.aspx)
- [Current deployment configuration](https://7xpydh.sharepoint.com/sites/ALM-Admin/Lists/ALMConfig/AllItems.aspx)
- [FetchXML pagination](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/fetchxml/page-results)
