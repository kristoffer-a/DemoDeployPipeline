# SDD ledger — plan: docs/superpowers/plans/2026-09-15-simple-alm.md

## Execution setup — 2026-09-15

Ruling: use this existing non-Git workspace and explicit file ownership — git rev-parse confirms no repository; plan explicitly permits this — no Git diff/commit evidence will be available.

Ruling: the planning-turn prohibition on tenant writes is historical; current user requests execution. Pending feature choices remain pending under the user's confirmation requirement.

## Preflight plan scan

| Task/interface | Check and result |
|---|---|
| 1 | Read-only inventory; unknown identities stay unknown. Pending choices prevent full acceptance. |
| 2 | Site/config/library creation and readback agree; TEST remains empty. |
| 3 | Publisher/solution/variables agree, dependent on accepted names and variables. |
| 4 | Gallery-only app matches read-only scope; publish/play required. |
| 5 | Deterministic first row and empty branch checks agree; restore temporary filter. |
| 6 | Export excludes transported DEV values while retaining working DEV runtime. |
| 7 | TEST preparation occurs after foundation; detailed Phase 2 design still requires acceptance. |
| 1 → 2–7 | Inventory provides target identities/access; no consumer may assume unknown IDs. |
| 2 → 3,4,5,6,7 | SharePoint IDs/schema feed bindings and verification; TEST provisioning deferred to 7. |
| 3 → 4,5,6,7 | Exact variable and connection identities shared by both consumers/import proof. |
| 4,5 → 6,7 | Published app and restored flow supply runtime evidence. |
| 6 → 7 | Export baseline precedes TEST binding proof; foundation alone cannot prove rebinding. |

## Tasks

- Task 1: in progress — local authenticated-tool preflight and browser access inspection.
- Tasks 2–7: not started.
- Pending setup question sent; no dependent writes until resolved.

### Task 1 observations

Browser verified all three supplied URLs, distinct environment/organization GUIDs, Ready Developer state and Dataverse enabled. Evidence: [browser-preflight.md](browser-preflight.md). SharePoint admin access works; active-site search ALM- returned zero results. Pending: ownership/design answers, deleted-site reservations, resource collisions, Dataverse roles, connections, DLP and entitlement.

Local agent reports PAC token expired and no target profiles. Ruling: retain browser as supported implementation path; PAC login is optional until a concrete required operation lacks a browser path. Do not change unrelated existing profiles.

SDD script adaptation: inspected sdd-workspace; it requires git rev-parse and Bash. Repository is absent. Use this plan-linked ledger and bounded brief/report files in docs/alm under the plan's explicit non-Git rule; no Git repository created.

Independent reviewer preflight_review: PASS for bounded partial preflight, no material findings. Renamed approvedUrls to observedUrls for evidence precision. Controller JSON verification: three environments, three distinct environment IDs, three distinct organization IDs, pending owner, zero approved proposed sites. Full Task 1 remains incomplete; Tasks 2–7 not started.

## 2026-09-16 continuation

User accepted all foundation defaults and verified account/owner kriall076@7xpydh.onmicrosoft.com. Skill discovery/install/spec update complete; see abilities.md. Independent skill_readiness review passed project-scoped BUNDLE routing; live MCP still unverified.

Ruling: start Task 2 after its own SharePoint access/collision checks while Dataverse-specific Task 1 checks remain pending — those checks do not protect or affect SharePoint-only mutations; require them before Task 3. No full preflight-complete claim.

Task 2: in progress — sharepoint_foundation agent owns browser and tenant writes, report sharepoint-foundation.md. Controller owns local docs/config. No further foundation approval needed.

## Resumed after usage interruption — 2026-09-16

- Re-read durable evidence and resumed the existing sharepoint_foundation implementer, retaining exclusive browser/tenant write ownership. All three sites already exist; inspect contents before creating anything to avoid duplicates.
- Task 2 remains incomplete pending ADMIN/DEV contents and TEST readback. See sharepoint-foundation.md for incremental evidence.
- Azure CLI installer session completed successfully. Installed executable verified with az version: 2.90.0. Initial sandboxed invocation could not initialize the normal .azure user folder; approved elevated verification succeeded. Authentication has not been performed.
- Canvas/FlowAgent MCP tool discovery still returns no exposed tools in this session. Skills are installed; configured MCP readiness remains separate.

Azure CLI account check completed: no signed-in account (az login required). Deferred browser authentication while Task 2 owns Chrome. SharePoint implementer reported ALMConfig created; remaining schema/content work is ongoing.

Task 2: complete (non-Git workspace; final task-2-review.md PASS, no open findings). Three sites, ADMIN config/libraries, DEV seed rows, TEST clean state and memberships verified. Browser ownership transferred to demo_components for Task 3. Task 3 dispatched with task-3-demo-brief.md; outputs demo-components.json and task-3-report.md.

Task 3 blocked on DEV Dataverse access: correct environment verified, but solution/publisher queries fail. Direct org error reports user de4edcb3-31b1-f111-aaac-002248f40b2b has no security roles and lacks prvReadEntity. No Task3 tenant writes. Implementer is confirming UPN/role UI read-only and completing evidence; do not assign roles without explicit authorization.

Task 3 final report BLOCKED BEFORE WRITE; approved UPN confirmed, PPAC role/user UI cannot load. Browser ownership released. User asked to choose admin-assigned System Customizer or explicitly authorize DEV-only System Administrator self-service. No role change performed. Resume same implementer after access is resolved. Actual Products GUID 54358b50-7727-4a83-adc9-d76dbed307e3 recorded in demo-components.json.

User reports roles added and requests continuation. Resumed demo_components for fresh DEV access verification and Task3 execution. No agent role changes authorized or needed. Browser ownership transferred to demo_components.

Task3 milestone: fresh DEV access works for approved account. No Demo/dev collisions. Publisher dev (prefix dev, generated choice prefix 77573) and unmanaged Demo 1.0.0.0 created; solution ID 90b3512e-19b2-f111-aaac-002248f40b2b verified. Variables/reference in progress; not task-complete.

2026-09-17 usage recovery: resumed existing demo_components agent. Durable JSON confirms publisher/Demo/connected SharePoint connection/Site variable; List variable and reference pending. Requested live duplicate check before writes and replacement of stale Task3 blocked report. No new permission approval needed.

Task 3: complete 2026-09-17 (task-3-review.md PASS; no open findings). DEV publisher/Demo/Site and List variables/reference verified. Task4 dispatched to demo_canvas with task-4-canvas-brief.md; exclusive browser/tenant ownership transferred. Tasks5–7 not started.

Task 4 complete: task-4-review.md PASS. Published app 3a38a583-a19b-41f9-816b-b101c1a505cb displays all three DEV products via Advanced Site/List variable bindings. Task5 assigned to demo_flow; exclusive browser ownership transferred. Scope manual first-product flow with nonempty/empty tests, restore filter.

2026-09-17 usage recovery: resumed demo_flow after credit error, same authorized Task5. Durable report has intended configuration only, no saved flow ID yet. Required live duplicate check before creation; exclusive browser ownership retained by demo_flow.

Task5 browser authoring blocked before save after embedded/direct designer failures; no confirmed flow ID/runs, details demo-flow.md. Controller completed authorized Azure CLI device login via Microsoft UI; approved UPN/tenant verified. Power Automate token acquisition succeeds (only tenant/expiry emitted). skill_readiness diagnoses local bundled FlowAgent stdio invocation read-only; no tenant writes during diagnostic.

FlowAgent recovery verified: pinned server initializes and exposes 59 schema-bearing tools through docs/alm/flowagent-mcp-client.mjs (real stdio MCP, no guessed API). Readiness evidence in flowagent-readiness.md. Resumed demo_flow with explicit DEV target, live duplicate check, actual metadata and mutation-timeout readback constraints. Browser remains idle; tenant API mutation ownership demo_flow. Current Azure CLI approved account/token access verified.

Task5 validation passed, but preflight blocked: list_connections targets unexpected tenant bf1275c5-f48d-4a09-89e3-8eedd5102fbd despite host Azure CLI approved tenant. No tenant mutation submitted. skill_readiness investigating distinct FlowAgent credential source read-only; do not alter unrelated PAC profiles. Draft task-5-create-args.json contains temporary hardcoded DEV input values for stopped initial flow, not final approved variable-bound configuration; final binding must be fixed/verified after solution addition before completion.

2026-09-18 compaction checkpoint: user requested handoff preparation. HANDOFF.md rewritten with complete verified state, actual IDs, auth incident boundary, unsubmitted draft caveats and next steps. auth-incident.md records observed calls and failed wrong-context read; no FlowAgent mutation submitted. No agents running (skill_readiness errored on credits), no tenant/browser writer currently assigned. Resume LOCAL auth-source diagnosis before any tenant calls. Existing task reviews 2–4 PASS; Task5 blocked, 6–7 unstarted.

## 2026-09-18 authentication recovery and second compaction checkpoint

- Root cause proven locally: Flow/Dataverse used Azure CLI while connection discovery used the separate global FlowAgent MSAL cache, whose sole account was `kristoffer.allaker@crmkonsulterna.se` in tenant `bf1275c5-f48d-4a09-89e3-8eedd5102fbd`.
- User changed the required continuation identity to `bosso@7xpydh.onmicrosoft.com` and prohibited every other authentication. An isolated Azure profile and isolated FlowAgent MSAL/token caches were created under the project-scoped local FlowAgent cache root; global/PAC profiles were not changed.
- Azure, Flow-token, MSAL, and Dataverse-first paths verified bosso in tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`. Project config/helper/proxy now pin official endpoints/client/tenant/caches, allow only known DEV/TEST/ADMIN target IDs, recheck authentication per tenant-capable call, block reconnect/bootstrap, and redact token-like output. Hermetic tests pass 4/4; independent security review reports no remaining reviewed account/tenant or covered-token-disclosure path.
- Hardened Task5 preflight: duplicate `list_flows=[]`; valid GetItems metadata; `resolve_refs` found `dev_SharePoint` -> `2a3c71eab7b44af482c2d87154edc8ee`; bosso `list_connections=[]`; `validate_flow valid:true`; `preflight_flow overall:block`, connection missing, `0/1 Connected`. No mutation submitted; no unknown mutation outcome.
- User explicitly approved creating a new SharePoint Online connection owned by bosso and rebinding existing DEV `dev_SharePoint`. User then requested compaction before continuation. Approval remains valid but unexecuted. No agent, browser writer, shell session, or tenant mutation is active at checkpoint.

## 2026-09-20 Task 5 portable continuation checkpoint

- Hermetic auth-policy tests passed 4/4 before tenant work. Fresh guarded `whoami` repeatedly verified `bosso@7xpydh.onmicrosoft.com`, tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`, approved DEV, and `identityMismatch:false`.
- Required pre-write readbacks passed: exact-name `list_flows` for `Demo - Get First Product` returned `[]`; pre-create SharePoint `list_connections` returned `[]`.
- The already-approved guarded `create-only` lifecycle created SharePoint connection `shared-sharepointonl-4f3b8a9e` silently. Fresh inventory independently read it back as `Connected`, with bosso as display/account/owner email. This is the only post-checkpoint tenant mutation submitted and its outcome is known.
- `dev_SharePoint` was **not rebound**, no flow was created or changed, and no run was started. Flow ID remains `null`; there is no unknown mutation outcome.
- The user reported completing bosso authentication in Chrome, but Chrome subsequently disappeared from the Codex browser inventory before the visible maker account/environment could be independently verified. One permitted retry again returned only the Codex in-app browser; tenant/UI work stopped immediately.
- Another-machine continuation: do not copy project-scoped Azure/MSAL/token cache directories or any browser credentials. Establish fresh guarded bosso authentication locally, run `node --test docs/alm/flowagent-auth-policy.test.mjs`, verify guarded `whoami`, connect Chrome, and visibly verify bosso plus approved DEV before mutation. Then rebind only `dev_SharePoint` to `shared-sharepointonl-4f3b8a9e`, read back Connected, and rerun duplicate/inventory/resolve/validate/preflight before creating the stopped flow. Use only `docs/alm/flowagent-mcp-client.mjs` or the guarded MCP entrypoint.
- Git portability preparation: initialized branch `main`; added a root README, machine-local/credential ignore rules, and a `.codex/config.example.toml`. `.tooling/`, `.playwright-mcp/`, `.codex/config.toml`, and authentication caches are excluded. No Git remote or commit is recorded at this checkpoint.
