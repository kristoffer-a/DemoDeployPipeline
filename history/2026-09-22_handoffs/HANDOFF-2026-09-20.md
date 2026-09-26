# Resume ALM implementation

Updated 2026-09-20 after guarded bosso connection creation and loss of the Chrome automation binding. This is the authoritative portable continuation checkpoint; older planning-only, wrong-auth-blocked, and pending-connection-choice status is superseded.

## First action after resume

Resume Task 5 with one bounded subagent as the sole tenant/browser writer. Before any tenant call, read auth-incident.md, demo-flow.md, flowagent-auth-policy.mjs, flowagent-tenant-guard.mjs, and flowagent-mcp-client.mjs; run the local hermetic guard test. Use only `docs/alm/flowagent-mcp-client.mjs` or the guarded MCP entrypoint. Never use global Azure/PAC/MSAL profiles, never call another tenant/account, never use `reconnect`, and stop immediately if any identity differs from `bosso@7xpydh.onmicrosoft.com` / `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`.

The user explicitly approved creating a new SharePoint Online connection owned by `bosso@7xpydh.onmicrosoft.com` and rebinding the existing DEV `dev_SharePoint` connection reference to it. Do not ask again. The guarded create-only lifecycle created `shared-sharepointonl-4f3b8a9e`; fresh inventory read it back as Connected and owned/displayed by bosso. Rebinding is not executed. On 2026-09-20 fresh guarded `whoami` was exact-approved, and the user reported completing bosso authentication in Chrome, but Chrome was absent from the automation inventory before its account/environment could be independently verified. No mutation followed. On resume or another machine, connect Chrome to Codex, open the Demo solution, verify visible `bosso@7xpydh.onmicrosoft.com` and DEV, then rebind only `dev_SharePoint` to this connection and read back the reference before flow creation. If any other identity/tenant appears, or rebinding would affect an unapproved component or needs a permission/role change, stop and report the exact mismatch/change.

## Completed / remaining

- Task 1 partial: all three environment identities verified; DEV authoring/SharePoint access works after user assigned roles. Do not claim a full role/DLP/entitlement audit, particularly ADMIN/TEST.
- Tasks 2–4 COMPLETE, independent reviews PASS: three SharePoint sites and contents, DEV solution/publisher/bindings, published gallery app.
- Task 5 NOT CREATED: no saved flow ID, no rebind/flow mutation submitted, no unknown mutation outcome, no run evidence. Under the hardened bosso guard, fresh exact-name `list_flows` returned `[]`; pre-create `list_connections` returned `[]`; the approved lifecycle then created and verified Connected bosso connection `shared-sharepointonl-4f3b8a9e`. The old `dev_SharePoint` reference remains to be rebound after the Chrome UI identity/environment is independently verified.
- Tasks 6–7 not started: unmanaged export/inspection and foundation regression, then separate TEST preparation/import/rebinding proof.
- Tasks 8–11 are roadmap only. Detailed ADMIN deployment design still needs later acceptance.

## Accepted scope (do not ask again)

Group-free team sites /sites/ALM-Admin, /sites/ALM-Dev, /sites/ALM-Test; owner kriall076@7xpydh.onmicrosoft.com; publisher dev/prefix dev; unmanaged DEV Demo 1.0.0.0; Site + List environment variables; corrected Dev SharePoint config field; managed TEST import; separate TEST Products setup after foundation. Stable core only, no extra features.

## Tenant / target identities

Approved account for continuation: bosso@7xpydh.onmicrosoft.com. Earlier artifacts were created under kriall076@7xpydh.onmicrosoft.com; do not use that account for new tenant calls.
Approved tenant: 7xpydh.onmicrosoft.com, 1c5afb69-a82c-4c81-b2cc-743ce7f91dac.
SharePoint: https://7xpydh.sharepoint.com/

| Role | Dataverse URL | Environment ID |
|---|---|---|
| DEV | https://devorgf20ef6ea.crm17.dynamics.com | 8f7d7c0e-e59d-e988-9dde-4ca7428aa659 |
| TEST | https://testorg5fd244de.crm17.dynamics.com | 8fcc484b-d74e-e479-84da-ad5a78d6d55b |
| ADMIN | https://adminorg774eae27.crm17.dynamics.com | f2280ea5-6793-e664-8f21-ea3ba6a4cb5c |

## Actual DEV artifacts

- Publisher dev: 42307624-19b2-f111-aaac-002248f40b2b.
- Demo solution: 90b3512e-19b2-f111-aaac-002248f40b2b, unmanaged 1.0.0.0.
- Products list: 54358b50-7727-4a83-adc9-d76dbed307e3; rows DEV - Apple, DEV - Banana, DEV - Coffee.
- Variables dev_SharePointSite and dev_ProductsList: DEV current values, no defaults, Export value No. Reference dev_SharePoint.
- Existing SharePoint connection ID resolved through Dataverse: 2a3c71eab7b44af482c2d87154edc8ee (earlier UI represented GUID with hyphens). It is not visible in bosso's connection inventory and preflight reports it missing. It must be replaced/rebound under the explicit approval above.
- Published app Demo Products: 3a38a583-a19b-41f9-816b-b101c1a505cb, solution component dev_demoproducts_9414e. Published playback shows all three DEV rows. Items = 'SharePoint List'; Title2.Text = ThisItem.Title. Advanced datasource pickers selected existing variables.
- Last verified Demo membership: 4 components (app, 2 variables, reference), no cloud flow.

## Flow continuation details

Read task-5-flow-brief.md, demo-flow.md, task-5-create-args.json, task-5-validate-args.json, task-5-preflight-args.json. The bosso connection already exists and is verified Connected; do not create a duplicate. First rebind `dev_SharePoint` to it and rerun duplicate check, connection inventory, resolve_refs, validation, and preflight. Draft create args are NOT final approved bindings: they use the old connection ID plus hardcoded DEV Site/List for an initial stopped flow; replace them with the new reference and proper variable bindings before acceptance/export. FlowAgent create_flow has no solution selector; final flow must be added to Demo via supported solution UI and membership/bindings verified. Never submit the draft blindly.

Final flow: manual trigger; Get_items uses existing variables/reference, ID asc, Top1; condition empty(body('Get_items')?['value']); true Compose null, false Compose first(...). Test nonempty, temporary no-match filter, restore unfiltered and rerun. No tests have run yet.

## Tooling

Five Microsoft skills installed/verified. See abilities.md and skills-source-revision.txt. On this machine the full PLUGIN_ROOT is under .tooling/power-platform-skills-a804d33267c973314e21f56827e0743ee3f1e690/plugins/{canvas-apps,power-automate}. `.tooling/` is intentionally excluded from Git; reinstall this pinned revision on another machine.

Local helper docs/alm/flowagent-mcp-client.mjs calls the official bundled server over stdio MCP; handshake succeeded with 59 schemas. Machine-local `.codex/config.toml` routes native FlowAgent through `flowagent-tenant-guard.mjs`; the repository contains only `.codex/config.example.toml`. The helper/proxy pin tenant, account caches outside the repository, official commercial endpoints, first-party client ID, and approved DEV/TEST/ADMIN IDs; recheck identity per tenant-capable call; block `reconnect`; redact token-like output; and reject unknown target environments. `node --test docs/alm/flowagent-auth-policy.test.mjs` passed 4/4. Independent final security review found no remaining reviewed path to another account/tenant or covered-token disclosure. Preserve these files and do not bypass them.

The isolated Azure CLI profile, Flow token, and isolated FlowAgent MSAL cache all verify `bosso@7xpydh.onmicrosoft.com` in the approved tenant; `whoami` reported `identityMismatch:false`. The global MSAL cache and older profiles remain unrelated and untouched. PAC profiles remain unrelated/expired; leave them unchanged. Browser authoring worked for the app but failed for flow embedded/direct designers; avoid repeating those same stalled steps. No active shell session or pending mutation needs recovery.

## Evidence / agent recovery

Read progress.md, execution-ledger.md, auth-incident.md, sharepoint-foundation.md, demo-components.json, task-3-report.md, demo-app.md, demo-flow.md and task-2/3/4-review.md. Task4/5/6 briefs and review briefs are prepared. Spec/plan: docs/superpowers/{specs,plans}/2026-09-15-simple-alm.md.

No subagent is running at checkpoint. The Task 5 writer stopped cleanly before the reference rebind; the auth-guard reviewer completed and passed the final hardened design. Spawn/resume one Task 5 writer after compaction; do not repeat Tasks 2–4. Only one tenant/browser writer at a time, explicit ownership. Git was initialized on branch `main` on 2026-09-20 for a portable handoff; no remote or commit is recorded in this checkpoint.

Runtime ALM architecture remains ADMIN Microsoft Dataverse connector selected-environment asynchronous solution export/import, not PAC runtime. Payload/binary handling remains Task7 proof. TEST stays empty through foundation; do not pre-create unmanaged TEST Demo/publisher. No reliable context percentage is exposed; do not invent one. This file preserves recovery state.
