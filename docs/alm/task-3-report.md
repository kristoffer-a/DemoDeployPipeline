# Task 3 report — DEV Demo components

Status: **COMPLETE**, 2026-09-17.

## Target and access readback

- Maker environment: `dev-eu-6eea207f`.
- Dataverse URL: `https://devorgf20ef6ea.crm17.dynamics.com`.
- Environment ID: `8f7d7c0e-e59d-e988-9dde-4ca7428aa659`; organization ID: `e021aa4d-16b1-f111-aaa0-002248f24a5a`.
- Signed-in account: `kriall076@7xpydh.onmicrosoft.com`.
- Fresh access check succeeded after the user assigned roles. Publisher, solution, and component authoring pages loaded normally. This task made no permission change.

## Collision checks

- Publisher search showed no existing publisher with unique name `dev` before creation.
- Solution search showed 0 results for `Demo` before creation.
- Final solution readback contains exactly the three approved components, with no duplicate variable or connection reference.

## Created foundation

- Publisher `dev`: display name `dev`, prefix `dev`, choice value prefix `77573`, publisher ID `42307624-19b2-f111-aaac-002248f40b2b`.
- Unmanaged solution `Demo`: unique name `Demo`, version `1.0.0.0`, solution ID `90b3512e-19b2-f111-aaac-002248f40b2b`.
- SharePoint connection: account `kriall076@7xpydh.onmicrosoft.com`, state `Connected`; UI-derived connection ID `2a3c71ea-b7b4-4af4-82c2-d87154edc8ee`.
- `dev_SharePointSite`: data-source variable for SharePoint parameter `Site`; current value `https://7xpydh.sharepoint.com/sites/ALM-Dev`; no default; Export value `No`.
- `dev_ProductsList`: data-source variable for SharePoint parameter `List`, related to `dev_SharePointSite`; current value `Products` / list ID `54358b50-7727-4a83-adc9-d76dbed307e3`; no default; Export value `No`.
- `dev_SharePoint`: SharePoint connection reference bound to the connected approved account.

## Final membership evidence

The live `Demo` Objects page showed:

- All: `3`.
- Connection references: `1` — `SharePoint` / `dev_SharePoint`.
- Environment variables: `2` — `SharePoint List` / `dev_ProductsList`; `SharePoint Site` / `dev_SharePointSite`.

The connection-reference edit panel independently read back display name `SharePoint`, name `dev_SharePoint`, connector `SharePoint`, and account `kriall076@7xpydh.onmicrosoft.com`.

Environment-variable-definition and connection-reference record GUIDs are not exposed by the supported maker UI, so they remain `null` in `demo-components.json` with that reason. No DLP, connector authorization, or entitlement error appeared during creation and binding; this is operational evidence rather than a full policy audit.

No canvas app, cloud flow, TEST component, or permission assignment was created.
