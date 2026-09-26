# SharePoint foundation evidence

Status: complete, 2026-09-16.

## Collision check

- Active sites search for `ALM-`: `0 items found`.
- Deleted sites search for `ALM-`: `0 items found`.

## Sites

All three sites were created from SharePoint admin center **Browse more sites** using the **Team site** option whose description explicitly says it does not create a Microsoft 365 Group. The Active sites readback showed template **Team site (no Microsoft 365 group)**, Microsoft 365 group **No**, primary admin **Kristoffer Allåker**, and external sharing **Off**.

| Role | Display name | URL | Primary admin |
|---|---|---|---|
| ADMIN | ALM Admin | https://7xpydh.sharepoint.com/sites/ALM-Admin | Kristoffer Allåker (`kriall076@7xpydh.onmicrosoft.com`) |
| DEV | ALM Dev | https://7xpydh.sharepoint.com/sites/ALM-Dev | Kristoffer Allåker (`kriall076@7xpydh.onmicrosoft.com`) |
| TEST | ALM Test | https://7xpydh.sharepoint.com/sites/ALM-Test | Kristoffer Allåker (`kriall076@7xpydh.onmicrosoft.com`) |

No site IDs were exposed in the creation or Active sites UI, so none are recorded.

The Site access panel was read back on each site. In all three sites it showed **Kristoffer Allåker** under **Site owners - full control**, **None** under **Site members - limited control**, and **None** under **Site visitors - no control**. No membership, sharing, or unrelated permission changes were made after site creation.

## ADMIN content

### ALMConfig

- URL: https://7xpydh.sharepoint.com/sites/ALM-Admin/Lists/ALMConfig/AllItems.aspx
- List ID exposed by classic List Settings: `049eba5a-700e-44db-9d2b-4e95c3af51b6`.
- Built-in `ID` and `Title` were retained. `Title` is optional; the one route row uses `Demo` for readability.
- Modern form required-field asterisks and the creation-panel required switches confirmed all five custom fields are required.
- Classic List Settings field-edit links exposed the exact internal names below.

| Internal name | Type | Required | Demo value read back |
|---|---|---|---|
| `SolutionName` | Single line of text | Yes | `Demo` |
| `DevPowerPlatformUrl` | Hyperlink or Picture | Yes | `https://devorgf20ef6ea.crm17.dynamics.com` |
| `TestPowerPlatformUrl` | Hyperlink or Picture | Yes | `https://testorg5fd244de.crm17.dynamics.com` |
| `DevSharePointUrl` | Hyperlink or Picture | Yes | `https://7xpydh.sharepoint.com/sites/ALM-Dev` |
| `TestSharePointUrl` | Hyperlink or Picture | Yes | `https://7xpydh.sharepoint.com/sites/ALM-Test` |

The list grid showed exactly one row: Title `Demo`, SolutionName `Demo`, and the four URLs above.

### Libraries

- `Solutions`: https://7xpydh.sharepoint.com/sites/ALM-Admin/Solutions/Forms/AllItems.aspx
  - Library ID exposed by Library Settings: `15b0e795-69dc-49d6-bacd-fdb3f39b36db`.
  - Versioning Settings readback showed **Create major versions** selected and **Create major and minor (draft) versions** unselected. The current major-version limit is 500.
  - Empty at foundation completion; no solution ZIP has been exported yet.
- `DeploymentLogs`: https://7xpydh.sharepoint.com/sites/ALM-Admin/DeploymentLogs/Forms/AllItems.aspx
  - Library ID exposed by Library Settings: `119a12b3-5b7e-4151-afed-93b03d60a056`.
  - Empty library only, as required for this phase.

## DEV content

### Products

- URL: https://7xpydh.sharepoint.com/sites/ALM-Dev/Lists/Products/AllItems.aspx
- Created as a blank custom list. No custom columns were added; the new-item form exposed only the built-in `Title` field, and the default view did not display the built-in `ID` column.
- No list ID or row IDs were exposed in the required creation and readback UI, so none are recorded.
- The final list grid showed exactly these three rows and no others:
  - `DEV - Apple`
  - `DEV - Banana`
  - `DEV - Coffee`

## TEST content

- Site Contents URL: https://7xpydh.sharepoint.com/sites/ALM-Test/_layouts/15/viewlsts.aspx
- Final Site Contents readback showed only the built-in `Documents`, `Form Templates`, `Site Assets`, `Style Library`, and `Site Pages` libraries.
- No `Products` list or other custom content was present, and no TEST content was created during this task.
