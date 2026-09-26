# Demo first-product flow

Status: **paused because the bosso-authenticated Chrome session is unavailable to automation before the approved connection-reference rebind**, 2026-09-20.

## Target and scope

- DEV environment: `dev-eu-6eea207f` (`8f7d7c0e-e59d-e988-9dde-4ca7428aa659`)
- Solution: `Demo` (`90b3512e-19b2-f111-aaac-002248f40b2b`)
- Approved account: `bosso@7xpydh.onmicrosoft.com`
- Flow: `Demo - Get First Product`
- Flow ID: `null` — no flow mutation has been submitted.

## Intended configuration

- Manual trigger only.
- SharePoint `Get items` action renamed `Get_items`.
- Existing solution bindings: `dev_SharePointSite`, `dev_ProductsList`, and `dev_SharePoint`.
- Order By: `ID asc`; Top Count: `1`.
- Condition: `empty(body('Get_items')?['value'])`.
- True branch Compose expression: `null`.
- False branch Compose expression: `first(body('Get_items')?['value'])`.
- No app trigger, deployment worker, extra service, permission, connection, or unrelated component.

## Applied configuration and evidence

- Hardened, project-scoped authentication guard: all 2026-09-18 tenant calls below passed the exact approved account/tenant/environment gate before dispatch: `bosso@7xpydh.onmicrosoft.com`, tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`, DEV `8f7d7c0e-e59d-e988-9dde-4ca7428aa659`.
- Fresh authenticated duplicate readback: exact-name DEV query returned `[]`; no `Demo - Get First Product` flow exists before creation.
- Fresh connector metadata readback: `shared_sharepointonline` operation `GetItems`; action type `OpenApiConnection`; required parameters `dataset` and `table`; optional `$orderby` and integer `$top`.
- Fresh Dataverse-first reference resolution: connection `2a3c71eab7b44af482c2d87154edc8ee`, `source=Embedded`, `connectionReferenceLogicalName=dev_SharePoint`.
- Fresh pre-create connection inventory for `shared_sharepointonline`: `[]` for the approved account.
- Approved connection lifecycle mutation completed: `pick_or_create_connection` ran in `create-only` mode with browser opening disabled and returned `shared-sharepointonl-4f3b8a9e`, `status: Connected`, `authMode: silent`.
- Fresh post-create inventory independently read back that connection as `Connected`, with display name, owner email, and account name all `bosso@7xpydh.onmicrosoft.com` (owner display `bosse sson`).
- Rebinding `dev_SharePoint` has **not** been submitted. On 2026-09-20 fresh guarded `whoami` again verified bosso, the approved tenant, DEV, and `identityMismatch:false`. The user reported completing bosso authentication in Chrome, but Chrome then became unavailable to the automation inventory; only the Codex in-app browser was returned and the old Chrome handle reported `Browser is not available: 2`. Therefore the required visible UI account/environment verification could not be completed and no rebind was attempted. On another machine or resumed session, reconnect Chrome, open the Demo solution as bosso, and verify the visible bosso account plus DEV environment before any mutation.
- Offline validation: `valid: true`.
- Live DEV preflight: `overall: block`; `0/1 connection refs Connected`; `dev_SharePoint` / connection `2a3c71eab7b44af482c2d87154edc8ee` reported `status: missing`; remediation from FlowAgent was to select or create a connection. The user subsequently approved creating a new SharePoint Online connection owned by bosso and rebinding the existing `dev_SharePoint` reference. Connection creation is now executed and verified; the reference rebind remains pending visible bosso/DEV verification in a reconnected Chrome session.
- Duplicate inspection: **passed twice**. The live DEV `Demo` solution showed `Cloud flows (0)` before the first draft, and a fresh signed-in Chrome readback again showed `Cloud flows (0)` after the abandoned embedded draft.
- First supported path: Power Apps solution UI -> New -> Automation -> Cloud flow -> Instant. The embedded classic designer accepted the manual trigger, SharePoint `Get items`, `dev_SharePointSite`, `dev_ProductsList`, `ID asc`, and Top Count `1`. While entering the condition expression, the nested cross-origin designer stopped accepting reliable locator/coordinate input. The tab was closed without saving.
- Second supported path: the same solution-aware create URL opened directly in the approved signed-in Chrome profile. The top-level new designer remained responsive and accepted the manual trigger, SharePoint `Get items`, and `dev_SharePointSite` token. Its List Name dynamic-content picker repeatedly disappeared or timed out when selecting `SharePoint List (dev_ProductsList)`. A switch to the classic designer then timed out and reset the browser-control session before any save.
- Initial save and flow ID: **not completed**; no Save action succeeded and no flow ID was exposed.
- Nonempty run: not started because no saved flow exists.
- Temporary empty-branch run: not started because no saved flow exists.
- Final unfiltered restore and rerun: not started because no saved flow exists.

## Recovery state boundary

- The official pinned FlowAgent server is available only through the hardened authenticated local MCP helper. Flow creation remains stopped at the required preflight gate: validation passed, but the solution reference still targets the old missing connection.
- One approved 2026-09-18 tenant mutation was submitted and verified: creation of bosso's connected SharePoint connection `shared-sharepointonl-4f3b8a9e`. Flow ID remains `null`; no rebind or flow mutation has been submitted and there is no unknown mutation outcome.
- Approved next operation after Chrome is available and the visible maker account/environment are verified as bosso/DEV: rebind only the existing DEV `dev_SharePoint` reference to `shared-sharepointonl-4f3b8a9e`, then read back the reference as Connected. After that, rerun duplicate check, connection inventory, reference resolution, validation, and preflight before any create call.
- FlowAgent `create_flow` has no target-solution argument. After creation, the flow must be added to `Demo` through the supported solution UI and the existing environment-variable tokens saved there; final completion requires membership and binding readback.
- The browser failure is limited to the Power Automate authoring surface. Existing DEV solution/component readback remained available and showed the approved account and environment.
- Last authoritative tenant readback: `Demo` contained 4 objects and `Cloud flows (0)` after the first abandoned draft. The second direct draft never completed a Save action; a post-stall final count could not be taken after browser control timed out.
- Intended configuration above is **not** claimed as applied tenant state. No run result, returned Product ID/Title, connection-reference readback, or final-restored-flow evidence is claimed.
