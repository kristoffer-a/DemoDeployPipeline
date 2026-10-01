# ALM rollout recovery and qualification

Status: operator procedure for an undeployed candidate. The commands below generate or inspect
local artifacts unless explicitly marked as a live rollout. They do not authorize a tenant write.
Use only an approved isolated target profile; the baked-in ADMIN target is dry-run-only.

## Before a rollout

1. Select and review a specific isolated target profile and solution version. Do not rely on
   implicit/default settings. `pipeline.target` validates tenant, environment, organization and
   site URLs, approved account names, publisher, solution, connections and list IDs. Keep the
   profile used for the rollout with its evidence, subject to local secret-handling rules.
2. Back up the target's current solution package and record the current state before the first
   write: each flow's Dataverse `workflowid`, `clientdata` definition, `statecode`/`statuscode`,
   solution membership/version, connection bindings and relevant environment configuration.
   Verify that the backup is readable and tied to the intended environment. The deployment code
   does not create this recovery snapshot automatically.
3. Pause other deployments and target-state edits. `deploy.py` pauses the parent and checks its
   run history before replacing children, but there is no distributed deployment lock. The
   quiescence check fails closed on ambiguous duplicates, malformed inventory/history,
   unsafe/repeated/out-of-environment pagination, unknown run status, or active runs. Wait for
   every parent run to reach a terminal status and rerun from the beginning if it stops.
4. Review the exact candidate source, profile, package, activation manifest, connection bindings,
   environment values and planned flow states. Do not treat a passing unit suite, package hash,
   or successful scheduled run as runtime qualification.

## Safe local checks and plans

Run from the repository root. These commands do not call Dataverse or Power Automate:

```bash
python3 -m pytest pipeline/tests -q
python3 -m pipeline.deploy --dry-run --target-config <isolated-profile.json> --solution-version 1.1.0.0
```

The deployment dry-run validates and generates all candidate definitions in a fresh temporary
directory; it does not update `pipeline/definitions/` or contact a target. Use the same explicit
profile and version in the later reviewed rollout.

To inspect a managed artifact and bind its exact bytes to an activation manifest, create a local
descriptor with the artifact tool, then recheck it before planning an import:

```bash
python3 -m pipeline.artifacts build --zip <managed.zip> --manifest <activation.json> \
  --solution <solution-unique-name> --version <four-part-version> --descriptor <release-descriptor.json>
python3 -m pipeline.artifacts verify --zip <managed.zip> --manifest <activation.json> \
  --solution <solution-unique-name> --version <four-part-version> --descriptor <release-descriptor.json>
python3 -m pipeline.release --zip <managed.zip> --manifest <activation.json> \
  --descriptor <release-descriptor.json> --solution <solution-unique-name> \
  --version <four-part-version> --target-config <isolated-profile.json> --bindings <bindings.json>
```

The final command omits `--apply`, so it only validates inputs and prints a `Planned` record; it
does not request a token, import a package, or write a log. The descriptor detects mismatch between
the ZIP and manifest, but is not a signature; protect the descriptor separately from the package.
Do not claim a remotely hosted verifier: the user's selected verifier is local, and C1/C2
one-click imports remain disabled until approved hosting and authentication are available.

Qualification fixtures and bootstrap definitions are separate local generation steps. They are
not self-deployment mechanisms:

```bash
python3 -m pipeline.qualification --out <local-fixture-dir> \
  --solution ALMQualificationFixtures --fixture-ids <real-isolated-workflow-ids.json>
python3 -m pipeline.bootstrap --output <local-bootstrap.json> \
  --target-config <test-eu-isolated-profile.json>
```

The fixture generator requires four real, unique workflow IDs and writes inert source files only.
The bootstrap command writes one validated helper definition for the isolated TEST site. Provision
the engine's dependencies through this independently reviewed bootstrap/recovery path; the engine
must not be expected to import or provision itself. These commands do not deploy or run the helper.

## Rollout order and failure recovery

After a separately authorized live rollout begins, the deployment path behaves as follows. The
live command is intentionally omitted here; the commands above are offline checks and plans.

1. It requires an explicit isolated profile; the baked-in ADMIN profile is rejected for live
   deployment. It validates and builds candidate definitions before target writes.
2. It ensures the solution and connection references, locates the parent only inside that solution,
   pauses an active parent, then checks paginated Flow API run history. Active or unknown run
   states, ambiguous inventory, malformed history, or unsafe/repeated pagination stop the rollout.
3. It updates/creates child flows in declared order and activates each child. It writes the parent
   definition last while leaving the parent disabled, rebuilds the definitions with resolved child
   IDs, updates the solution version, then activates the parent as the final flow-state write.
4. It prints the resulting Dataverse workflow IDs. Capture them and read back all definitions and
   states against the pre-rollout backup and intended manifest before restoring traffic.

If any child or parent-definition operation fails after the parent is paused, deployment stops and
leaves the parent disabled. Do not retry blindly and do not assume rollback occurred. Keep the
parent off, inspect every child definition and state against the before-snapshot, identify the
partial write, and repair or restore children explicitly. Re-run only with the reviewed isolated
profile and explicit intended version after the target is coherent and quiescent. The tool does
not automatically roll back children, solution version, bindings, or prior successful writes.
There is no supported concurrent deployment or state-edit path.

If final parent activation fails after the solution version update, treat the rollout as partial:
leave the parent disabled, inspect and record the installed version and all child states, then use
the same recovery procedure. Do not manually enable the parent before the child/version readback
matches the intended release.

## Gates before enabling imports or expanding rollout

- **Import-time flow state:** qualify fresh import and update behavior with enabled and disabled
  inert flows, required connection bindings, and the activation manifest. `PublishWorkflows` does
  not control cloud-flow activation. The release runner currently rejects packages containing cloud
  flows; it can only import a validated flowless managed solution into an isolated target, and that
  write path is not runtime-qualified.
- **Isolated ALM runtime:** test Parse JSON schema support, child input binding, disable-before-
  enable reconciliation, readback, log/sidecar association, failure behavior and durations. Keep
  qualification data and notification destinations isolated.
- **Engine bootstrap:** provision its SharePoint lists/fields and target configuration using the
  independent bootstrap/recovery path. Verify readback before deploying ALMPipeline to depend on
  them. ALMPipeline cannot be the only way to recover its own prerequisites.
- **Products:** TEST `dev_ProductsList` is still a placeholder. Create and verify the real TEST
  Products list, update the TEST variable, and validate the app as a target user before claiming the
  business solution is operational.
- **FlowError:** reconcile the live scanner states with source-bound coverage evidence; complete
  same-flow recovery, notification retry, replay, over-900 backlog, overlong-ID, child-duration,
  coverage, owner and run-link acceptance. Keep the separate FlowError deployment blocked until
  those gates and its own source/export reconciliation are complete.
- **Promotion and automation:** protect release descriptors independently, qualify any import
  route end-to-end, and review CI identity, permissions, artifact custody and recovery. Local
  verifier preparation does not provide a remote service or authorize one-click imports.

Record the target ID, solution/version, before/after definitions and states, artifact hashes,
workflow IDs, run IDs, timestamps, operator and evidence links for each qualification or rollout.
Mark each result `unknown` until directly observed. Keep diagrams, live definitions and deployment
state unchanged until their separate reviews and approvals are complete.
