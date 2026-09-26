# Browser preflight — 2026-09-15

Controller inspected existing Chrome Power Platform admin session, refreshed the environment list, and read each detail page. No tenant resource writes.

Account panel: Kristoffer Allåker, kriall076@7xpydh.onmicrosoft.com. Tenant link ID: 1c5afb69-a82c-4c81-b2cc-743ce7f91dac. This is browser identity evidence, not proof of local PAC authentication or connector ownership.

| Role | Verified host | Environment ID | Organization ID |
|---|---|---|---|
| ADMIN | adminorg774eae27.crm17.dynamics.com | f2280ea5-6793-e664-8f21-ea3ba6a4cb5c | 2a49ea7b-18b1-f111-8add-0022486f7441 |
| DEV | devorgf20ef6ea.crm17.dynamics.com | 8f7d7c0e-e59d-e988-9dde-4ca7428aa659 | e021aa4d-16b1-f111-aaa0-002248f24a5a |
| TEST | testorg5fd244de.crm17.dynamics.com | 8fcc484b-d74e-e479-84da-ad5a78d6d55b | 2352de63-16b1-f111-8add-0022486f7065 |

All three: Developer, Ready, Dataverse enabled, Switzerland, Dataverse version 9.2.26085.142. Detail pages are available via https://admin.powerplatform.microsoft.com/manage/environments/environment/{environmentId}/hub?geo=Che.

SharePoint root https://7xpydh.sharepoint.com/ loaded successfully. SharePoint admin https://7xpydh-admin.sharepoint.com/_layouts/15/online/AdminHome.aspx#/siteManagement/view/ALL%20SITES loaded successfully. Settled Active sites search for `ALM-` reported `0 items found` and `We didn't find anything to show here`.

No active ALM site collision found; deleted-site URL reservations remain unchecked. Create command is visible, but site creation permission is not proven by a read-only visit. Site ownership still awaits user choice. Dataverse customization rights, publisher/solution collisions, connector ownership, DLP and license entitlement remain separate preflight checks.

Browser tab identifiers (ephemeral, rediscover if stale): existing Chrome PPAC tab 846601411; created SharePoint admin tab 846601421. Do not infer session persistence after this turn.
