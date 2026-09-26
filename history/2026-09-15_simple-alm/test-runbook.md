# Demo DEV to TEST deployment runbook

This runbook is executable only after the approved `bosso@7xpydh.onmicrosoft.com` identity, connector permissions, and target SharePoint connection are verified. It does not turn any unexecuted check into evidence.

## Preconditions

- Confirm the guarded identity is bosso in tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`.
- Confirm only the recorded DEV, TEST, and ADMIN environment IDs are accepted by the guard.
- Rebind DEV `dev_SharePoint` only to the approved bosso connection after visible DEV maker-portal verification.
- Prepare TEST `Products` separately with only compatible built-in `ID` and `Title` metadata and the sentinel `TEST - Tea`. Do not copy DEV rows.
- Record TEST SharePoint connection/reference mapping and verify the deployment identity can use it.

## First managed import

1. Complete and publish the Demo first-product flow. Run it against nonempty DEV data; temporarily use a nonmatching filter for the empty branch, then restore the final unfiltered definition and rerun it.
2. Freeze and publish DEV Demo. Export unmanaged and managed ZIPs from that same state. Inspect both archives; confirm exported variable definitions contain neither DEV current values nor DEV default fallbacks.
3. Archive both unchanged files below `Solutions/Demo/<version>/`, along with release metadata, target snapshot, SharePoint file unique ID, version ID, and SHA-256. Stop if that release path already exists.
4. From ADMIN, call the selected-environment Dataverse asynchronous export/download and import actions. Record export/import job IDs and the actual target variable and connection-reference mapping payloads.
5. Poll the server jobs to a terminal result. On an unresolved timeout, mark `NeedsAttention`; do not submit another import.
6. Verify TEST contains managed Demo at the expected version, effective TEST Site/List values, the TEST connection binding, and a ready flow.
7. Play TEST Demo Products and run the TEST flow: each must read `TEST - Tea`. Recheck DEV: it must still read DEV records.

## Repeat deployment

1. Make and publish one intentional DEV Demo update; increment the solution version.
2. Archive a new paired unmanaged/managed release without modifying the earlier release.
3. Request the configured route once, then repeat the same RequestId. Verify one deployment record/RunId only.
4. Verify TEST reflects the new managed version and TEST sentinel data, while DEV remains unchanged.

## Negative and recovery checks

- Invalid target configuration: request must reject it before queueing; arbitrary environment URLs are never accepted.
- Missing/unusable connection or incompatible TEST list schema: worker must fail before import and retain diagnostics/job IDs.
- Failed import: retain server error and import job ID; do not call it successful.
- Poll timeout: record `NeedsAttention`, inspect the existing job, and never blindly resubmit.
- Archived package retrieval: use stored file unique ID, version ID, and SHA-256 to retrieve and hash the exact managed ZIP used by the deployment.
- Access: where existing representative non-admin accounts permit it, verify they can request/read only the authorized configuration/run surfaces and cannot modify configuration or release artifacts.
