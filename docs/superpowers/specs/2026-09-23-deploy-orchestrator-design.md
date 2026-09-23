# Deploy orchestrator design

Date: 2026-09-23. Status: approved in chat, awaiting written review.
Builds on: `2026-09-15-simple-alm.md` and the ALMSpike results below.

## Goal

One click deploys a solution from DEV to a target environment. A parent flow runs export and
archive, then calls child flows for each deployment step. Each step can be switched on or off per
solution and target environment.

Scope of this design: piece 1 (parent + switches) and piece 2 (post-import children).
Out of scope, designed later: SharePoint deploy child (new/existing list), security group
management. App sharing (C4) is included only as a separate spike.

## Spike evidence (2026-09-23, ADMIN environment, account kriall076)

| Variant | Result | Time |
|---|---|---|
| A: two flows (export, import by ZIP path) | succeeded | 46 s + 63 s |
| B: one flow, two Dataverse connection references | succeeded | 85 s |
| C: parent + child, parent passes archived ZIP path | succeeded | 105 s (child 63 s) |

Chosen: **C**. The imported file is the archived file; the child can be run alone later to
re-import an older ZIP. TEST readback after each run: Demo managed 1.0.0.0, `dev_SharePointSite`
= ALM-Test, `dev_SharePoint` bound to TEST connection `shared-sharepointonl-0f567e53`.

Known constraint: `@odata.type` keys in `ComponentParameters` must be built as text with `@@odata`
and restored with `replace()` inside `json()`. See `spike/build_spike.py`.

## Decisions

1. Pattern C: parent flow calls child flows ("Run a Child Flow"), all in one solution.
2. Connections are created once per target environment and reused. Deployment never signs in.
   Connection IDs come from a config mapping, not from a run-time lookup.
3. Owner of target-environment connections: `kriall076@7xpydh.onmicrosoft.com` for now.
   Replace with a service account before any production use.
4. Switches: Yes/No columns on the `ALMConfig` row, one row per solution and target environment.
5. Archive: timestamped files `Solutions/<Solution>/<Solution>_managed_<yyyyMMdd-HHmmss>.zip`.
   This replaces the single `solution.zip` with SharePoint versions from the 2026-09-15 spec.

## Config (ALM-Admin SharePoint)

### `ALMConfig` (exists, add columns)

One row per solution and target environment, e.g. `Demo → TEST`, later `Demo → PROD`.

| Column | Type | State |
|---|---|---|
| `SolutionName` | text | exists |
| `DevPowerPlatformUrl`, `DevSharePointUrl` | hyperlink | exist (source) |
| `TargetEnvironment` | choice: TEST, PROD | new |
| `TargetPowerPlatformUrl`, `TargetSharePointUrl` | hyperlink | new |
| `RunImport` | Yes/No | new |
| `RunPostImport` | Yes/No | new |
| `RunShare` | Yes/No | new |
| `AppShareGroupId` | text (Entra group object ID) | new |

The existing `Test*` columns stay until the user approves removing them.

### `ALMConnections` (new)

One row per environment and connection reference. Shared by all solutions.

| Column | Example |
|---|---|
| `Environment` (choice) | TEST |
| `ConnectionReference` | `dev_SharePoint` |
| `ConnectionId` | `shared-sharepointonl-0f567e53` |
| `ConnectorId` | `/providers/Microsoft.PowerApps/apis/shared_sharepointonline` |

### `ALMVariables` (new)

One row per solution, environment and environment variable.

| Column | Example |
|---|---|
| `SolutionName` | Demo |
| `Environment` (choice) | TEST |
| `SchemaName` | `dev_ProductsList` |
| `Value` | TEST Products list ID |

## Flows (solution in ADMIN)

| Flow | Role | Switch |
|---|---|---|
| C1 Deploy (parent) | inputs: solution, target. Reads config, checks, exports, archives, calls children, writes log | always |
| C2 Import (child) | imports ZIP by path; builds `ComponentParameters` from `ALMConnections` + `ALMVariables` | `RunImport` |
| C3 Post-import (child) | 1. check connection references match `ALMConnections`; 2. set variable values from `ALMVariables`; 3. turn on solution flows that are off | `RunPostImport` |
| C4 Share app (child) | shares the canvas app with `AppShareGroupId` via Power Apps for Admins | `RunShare` |

C2–C4 use the Dataverse connector's selected-environment actions against the target URL, except
C4. C4 needs a spike first: confirm the Power Apps for Admins role-assignment action works from
ADMIN with kriall076.

Children take a manual trigger, use embedded connections, and end with "Respond to a PowerApp or
flow" returning `status` and `message`.

## Errors

1. Pre-checks in C1, before export: config row exists; every connection reference in the DEV
   solution has an `ALMConnections` row for the target; every environment variable in the solution
   has an `ALMVariables` row. Any gap stops the run with a message naming the missing row.
2. A child that fails terminates as Failed with the job message. The parent skips later children.
3. A final log step in C1 runs after success or failure.

## Logging

One JSON file per run in `ALM-Admin/DeploymentLogs`, named `<Solution>_<Target>_<yyyyMMdd-HHmmss>.json`:
run ID, solution, target, ZIP path, and per step: `ran | skipped | failed`, duration, message.

## Limits

A child must reply to its parent within 120 seconds. C2 took 63 s for Demo (41 KB ZIP). The log
records step durations. If C2 approaches the limit, change it to reply immediately and write its
own result to the log.

## Tests (Demo → TEST)

| # | Setup | Expected |
|---|---|---|
| 1 | all switches on | export, import, post-import, log all succeed |
| 2 | `RunImport` off | export and archive only; log shows import skipped |
| 3 | TEST `ALMConnections` row removed | stops before export with a named missing row |
| 4 | `RunImport` off, `RunPostImport` on, new list ID in `ALMVariables` | variable updated in TEST, no import |

## Cleanup (each needs user approval)

- Delete spike flows A1, A2, B (and C1/C2 once replaced).
- Rename `spike/build_spike.py` into the pipeline builder.
- Remove `Test*` columns from `ALMConfig`.
