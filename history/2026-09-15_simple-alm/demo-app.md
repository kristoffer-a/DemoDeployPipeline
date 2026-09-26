# Task 4 — Demo Products canvas app

Status: **COMPLETE**, 2026-09-17.

## Target and authorization

- DEV environment: `dev-eu-6eea207f` / `8f7d7c0e-e59d-e988-9dde-4ca7428aa659`.
- Dataverse URL: `https://devorgf20ef6ea.crm17.dynamics.com`.
- Solution: unmanaged `Demo` (`90b3512e-19b2-f111-aaac-002248f40b2b`).
- Signed-in account: `kriall076@7xpydh.onmicrosoft.com`.
- Authorized scope: create, publish, and play the gallery-only `Demo Products` canvas app in DEV.

## Collision and pre-create evidence

- The live `Demo` solution showed Apps `0` and exactly the three Task 3 foundation components before creation.
- The DEV environment-wide **My apps** page showed `No apps yet`; no interrupted `Demo Products` draft existed.
- The app was started from **Demo > New > App > Canvas app**, so the solution context was preserved.
- Canvas app name: `Demo Products`; default tablet format retained.

## Build progress

- Power Apps Studio opened successfully for `Demo Products`.
- First save completed and assigned app ID `3a38a583-a19b-41f9-816b-b101c1a505cb`.
- Existing SharePoint connection `kriall076@7xpydh.onmicrosoft.com` was selected.
- In the SharePoint site picker, **Advanced** exposed the existing `SharePoint Site` environment variable with help value `https://7xpydh.sharepoint.com/sites/ALM-Dev`; that variable was selected.
- In the list picker, **Advanced** exposed the existing `SharePoint List` environment variable; that variable was selected and connected.
- Studio added data source identifier `SharePoint List` and confirmed: `The data source "SharePoint List" was added to your app.`
- `Gallery1.Items` is `'SharePoint List'`; the formula bar reported data type `Table` and no formula error.
- The gallery uses the **Title** layout. Default rectangle, separator, and arrow controls were removed, leaving one label, `Title2`.
- `Title2.Text` is `ThisItem.Title`.
- `Gallery1.AccessibleLabel` is `"Products"` and `Gallery1.TabIndex` is `0`.
- Authoring-canvas live data renders `DEV - Apple`, `DEV - Banana`, and `DEV - Coffee`.

## Validation and publish evidence

- Final save readback: `All changes are saved`, timestamp `9/17/2026, 12:40:39 AM`.
- App checker after the final fixes showed no count for Formulas, Runtime, Performance, or Data source and only Accessibility `(1)`. The remaining accessibility item is a tip to revise the default `Screen1` name; the earlier missing-accessible-label and missing-tab-stop errors were resolved.
- Publish readback: `Publish successful` and `9/17/2026, 12:41:14 AM Demo Products is now available to everyone.`
- Final live `Demo` solution membership: All `4`, Apps `1`, Connection references `1`, Environment variables `2`.
- Canvas app solution component: display name `Demo Products`, name `dev_demoproducts_9414e`, type `Canvas App`, managed `No`, customized `Yes`, owner `Kristoffer Allåker`.
- Published player URL resolved to app ID `3a38a583-a19b-41f9-816b-b101c1a505cb` in DEV environment `8f7d7c0e-e59d-e988-9dde-4ca7428aa659`.
- First published play prompted for the existing connected SharePoint account and declared read-record access; the approved connection completed successfully.
- Published playback rendered exactly three gallery rows: `DEV - Apple`, `DEV - Banana`, and `DEV - Coffee`.

## Binding conclusion

The app uses the solution's existing SharePoint Site and SharePoint List environment variables selected through Studio's Advanced pickers. The gallery binds to the resulting `SharePoint List` data source as `'SharePoint List'`; no DEV URL or list GUID is hardcoded in the app formula.
