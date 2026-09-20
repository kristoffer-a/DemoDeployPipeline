# Authentication mismatch incident

Checkpoint 2026-09-18. Source: controller command results, demo_flow audit-only report, pinned FlowAgent source, and redacted local cache metadata; no independent tenant audit-log review has been performed.

## Root cause established locally

The mismatch came from FlowAgent's split authentication paths. Flow and Dataverse requests use Azure CLI tokens, while connection discovery uses a separate MSAL cache for `https://api.powerplatform.com`. The global MSAL cache was `common.json` and contained one account: `kristoffer.allaker@crmkonsulterna.se` in tenant `bf1275c5-f48d-4a09-89e3-8eedd5102fbd`. The Azure CLI profile and FlowAgent Azure-token caches instead belonged to tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`.

The source confirms `list_connections` uses the MSAL-backed connectivity path, while `resolve_refs` tries Dataverse/Azure CLI first. This explains why flow/Dataverse checks could succeed in 7xpydh while `list_connections` used the unrelated tenant. `whoami` checks only the Flow/Azure CLI token and could not expose the connection-token mismatch.

The current user instruction supersedes the earlier account choice: all future tenant access must use `bosso@7xpydh.onmicrosoft.com` in the same approved tenant. The previous `kriall076@7xpydh.onmicrosoft.com` Azure profile is therefore also disallowed for continuation.

Project-scoped isolation is installed in `.codex/config.toml` and `flowagent-mcp-client.mjs`: dedicated Azure, FlowAgent token, and FlowAgent MSAL cache directories plus an explicit tenant/default-environment pin. `flowagent-tenant-guard.mjs` refuses to start unless both isolated caches identify only `bosso@7xpydh.onmicrosoft.com` in the approved tenant.

The isolated sign-ins are now complete and verified. Local metadata identifies only `bosso@7xpydh.onmicrosoft.com` in tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`; FlowAgent `whoami` reports the same Azure identity and Flow-token tenant with `identityMismatch:false`; the MSAL-backed approved-DEV `list_connections` request completed without a tenant mismatch; and Dataverse-first `resolve_refs` returned the existing `dev_SharePoint` reference and connection ID. The connection listing for bosso was empty, while the Dataverse solution reference remains discoverable.

## Facts

Approved tenant: 7xpydh.onmicrosoft.com / 1c5afb69-a82c-4c81-b2cc-743ce7f91dac. Approved account for continuation: bosso@7xpydh.onmicrosoft.com. Earlier artifacts were created under kriall076@7xpydh.onmicrosoft.com.

FlowAgent list_connections requested DEV environment 8f7d7c0e-e59d-e988-9dde-4ca7428aa659 and returned ServiceToServiceEnvironmentNotFound: environment could not be found in tenant bf1275c5-f48d-4a09-89e3-8eedd5102fbd. Local redacted cache metadata established the credential source as FlowAgent's global `common.json` MSAL cache and associated it with `kristoffer.allaker@crmkonsulterna.se`; the tenant's display name was not queried.

A read-only request used the wrong tenant authentication context. It was rejected. No connections, flows or records from that tenant were returned in the recorded output; the tenant ID appeared in the error. No FlowAgent tenant mutation was submitted. Earlier completed SharePoint/solution/app writes were in approved 7xpydh targets.

## Recorded Task5 calls

| Call | Outcome |
|---|---|
| sandboxed whoami | azIdentity/tokenIdentity null; no successful identity resolution |
| sandboxed list_flows | token-failed; no tenant data |
| host-authenticated list_flows, exact DEV/name | successful empty array [] |
| get_operation_details, SharePoint GetItems | connector operation metadata returned |
| resolve_refs, intended DEV | existing approved connection/reference mapping returned |
| validate_flow | local validation valid:true |
| preflight_flow, DEV | overall:block, missing connection diagnostics |
| list_connections, DEV | wrong-tenant environment-not-found error above |
| create/update/publish/run/delete | none submitted |

Azure CLI account and Power Automate token metadata independently showed approved tenant/account, but this did not establish every internal FlowAgent authentication path. Earlier local preflight observed unrelated PAC auth profiles; their involvement is unproven.

## Next step and boundary

Task 5 may resume only through the guarded project helper or guarded MCP entrypoint. Do not call or authenticate into the unrelated tenant, dump credential files/tokens, clear unrelated caches, or change unrelated profiles. Stop immediately if any path reports an account or tenant other than `bosso@7xpydh.onmicrosoft.com` / `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`.

User was told about the failed wrong-context read, no returned tenant data, and no wrong-tenant writes. Preserve this distinction; do not claim no request occurred.
