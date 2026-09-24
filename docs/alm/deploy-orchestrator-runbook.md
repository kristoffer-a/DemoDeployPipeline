# Deploy orchestrator runbook

Deploys a solution from DEV to a target environment with one click on flow **ALM C1 - Deploy (parent)** in ADMIN.
Design: `docs/superpowers/specs/2026-09-23-deploy-orchestrator-design.md`. Plan: `docs/superpowers/plans/2026-09-24-deploy-orchestrator.md`.

## 1. Prerequisites

- `az login` into tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`. Every script stops if az shows another tenant.
- Account: `kriall076@7xpydh.onmicrosoft.com`. This is the user's explicit exception to the bosso-only rule for this work; replace it with a service account before production.
- ADMIN connections owned by kriall076: Dataverse `shared-commondataser-88f9738e`, SharePoint `shared-sharepointonl-a0f00819`.
- One connection per connector in each target environment, created once by a person, e.g. TEST SharePoint `shared-sharepointonl-0f567e53`. Deployments never sign in; they only bind.

## 2. Configure a solution and target (ALM-Admin SharePoint)

| List | One row per | Columns |
|---|---|---|
| `ALMConfig` | solution × target | `SolutionName`, `DevPowerPlatformUrl`, `DevSharePointUrl`, `TargetEnvironment` (TEST/PROD), `TargetPowerPlatformUrl`, `TargetSharePointUrl`, `RunImport`, `RunPostImport`, `RunShare`, `AppShareGroupId` |
| `ALMConnections` | environment × connection reference | `Environment`, `ConnectionReference`, `ConnectionId`, `ConnectorId` |
| `ALMVariables` | solution × environment × variable | `SolutionName`, `Environment`, `SchemaName`, `Value` |

Edit rights on these ALM-Admin lists are deployment rights: the rows in `ALMConnections`/`ALMConfig` decide which target URLs and connections a deployment writes to, so treat list-edit access the same as deploy access.

Edit rows in SharePoint directly. For scripted changes (the browser pane can't reach SharePoint), use the setup flow - which is a **Demo → TEST test/admin helper, not a general config tool**: `provision` and `config` are hard-pinned to solution `Demo` and target `TEST`.

```bash
python3 -m pipeline.sp_setup config RunImport=false RunPostImport=true
```

Then run flow **ALM Setup - SharePoint config** (FlowAgent `run_flow`, env ADMIN), and read the result with `python3 -m pipeline.flowapi <flow> <run> Results`. Other commands: `provision`, `connection-env TEST|PROD`, `variable NAME=VALUE`, `readback`.

## 3. Deploy the flows

```bash
python3 -m pytest pipeline/tests -q
```

```bash
python3 -m pipeline.deploy
```

This deploys C2, C3, then C1 into solution `ALMPipeline` and prints each flow's Power Automate ID. `--dry-run` writes the same JSON to a fresh temp directory (`tempfile.mkdtemp(prefix="alm-defs-")`, printed by the command) instead of `pipeline/definitions/`, so it never overwrites the committed definitions - those carry real, already-deployed child workflow ids that a dry run has no ids to substitute for.

## 4. Run a deployment

- Portal: run **ALM C1 - Deploy (parent)**. Inputs are Solution (default `Demo`) and Target (default `TEST`).
- API: FlowAgent `run_flow` on C1. Inputs can't be passed as kriall076, so the defaults apply.

C1 order: pre-checks (config row, mapping rows for every connection reference and variable in the DEV solution) → export managed → archive `Solutions/<Solution>/<Solution>_managed_<time>.zip` → C2 import (if `RunImport`) → C3 post-import (if `RunPostImport`) → log.

Read the run log:

```bash
python3 -m pipeline.flowapi <C1 flow id> <run id> Log_entry
```

The same JSON is saved as `DeploymentLogs/<Solution>_<Target>_<time>.json` in ALM-Admin.

## 5. Verify the target

```bash
python3 -m pipeline.verify_target
```

It shows the Demo solution (managed, version), the last import job, the `dev_*` variable values, the `dev_*` connection bindings, and the cloud flow states in TEST.

## 6. Known limits

- A child flow must reply within 120 s. Demo's import took about 60 s. Children always reply, on failure too, so the parent never hangs. If a child does exceed 120 s, the built-in "Run a Child Flow" action itself fails in the parent (independent of the child's own reply), and the run log shows the corresponding stage - Import for C2, PostImport for C3 - as `Failed`, with `seconds` showing that stage's real elapsed time.
- Every failed ALM run in ADMIN opens a FlowAdmin-Monitoring incident and a Teams card (owned by the FlowError project).
- ADMIN's preferred solution is `Development` (not ours). `pipeline.deploy` always sends `MSCRM.SolutionUniqueName: ALMPipeline`.
- C4 (share app) is not built. See `docs/alm/c4-share-spike.md`.
- Service account still to replace kriall076.
- C3's flow turn-on step is untested live: Demo has no cloud flow in TEST to turn on, so that code path has only been validated by unit tests, not a real run.
- The setup flow (**ALM Setup - SharePoint config**) stays deployed in ADMIN after use - turn it off after each use and delete it at cleanup.

## Acceptance results (2026-09-24, Demo → TEST)

| # | Test | Run | Result |
|---|---|---|---|
| 1 | all switches on | `08584113808956253188916642923CU11` | ✅ export, import, post-import, log |
| 2 | `RunImport` off | `08584113807156571619694030554CU02` | ✅ import and post-import skipped, TEST import unchanged |
| 3 | TEST mapping row hidden | `08584113798300123008547905201CU30` | ✅ stopped before export: "Missing mapping rows for TEST: dev_SharePoint" |
| 4 | import off, post-import on, new variable | `08584113806260430767225925607CU28` | ✅ `dev_ProductsList` updated, no import |
| — | restore run | `08584113797947949442479376819CU26` | ✅ all green |
