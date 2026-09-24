# C4 share-app spike

Date: 2026-09-24. Environment: ADMIN. Account: kriall076. Research only: nothing was created.

## Action found

Connector **Power Apps for Admins** (`shared_powerappsforadmins`), operation `Edit-AdminAppRoleAssignment` ("Edit App Role Assignment as Admin": sets permissions for a Power App).

| Parameter | Required | Meaning |
|---|---|---|
| `environment` | yes | environment name (GUID) of the target, e.g. TEST `8fcc484b-d74e-e479-84da-ad5a78d6d55b` |
| `app` | yes | the app's name (GUID) in the target environment |
| `api-version` | no | default `2016-11-01` |
| `body` | no in schema, needed in practice | the role assignment: principal (group object ID) and role (CanView / CanEdit) |

Related: `Get-AdminAppRoleAssignment` reads the current sharing, so a re-run can check the result.

Power Platform for Admins V2 (`shared_powerplatformadminv2`, already connected) has only `Get-AdminApps` / `Get-AdminApp`. It can find the app ID in the target, but it can't share.

## Connection state

- ADMIN has **no Power Apps for Admins connection**. It must be created once by the user (sign-in). kriall076 needs the Power Platform admin (or environment admin) role.
- The Power Platform for Admins V2 connection `shared-powerplatform-7059808c` exists (kriall076, Connected).

## Recommendation: GO, with one prerequisite

Build C4 in a later plan:
1. Look up the canvas app `Demo Products` in the target (`Get-AdminApps`, filter by display name) to get its app name.
2. Call `Edit-AdminAppRoleAssignment` with `AppShareGroupId` from `ALMConfig` and the CanView role.
3. Reply with status and message (same child contract as C2 and C3).

Prerequisite: the user creates the Power Apps for Admins connection in ADMIN. The exact `body` shape for a group principal must be confirmed on the first live call.
