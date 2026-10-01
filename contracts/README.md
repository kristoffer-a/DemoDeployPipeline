# Flow activation contract v1

Status: implemented locally on `codex/flowadmin-deployment-contract`; not deployed or runtime-qualified. This is the first part of the platform release contract, not a complete module deployment manifest.

## Purpose

C3 previously enabled every disabled cloud flow in a solution. FlowAdmin deliberately keeps its legacy scanner stopped, and setup helpers also need independent desired states. A deployment must therefore declare each flow's state explicitly.

`flow-activation.schema.json` is the canonical schema. A runtime copy without regex properties is embedded in generated C1/C2/C3 Parse JSON actions. `examples/demo.activation.json` is the explicit empty policy for the flowless Demo fixture.

```json
{
  "version": 1,
  "solution": "Example",
  "flows": [
    {"workflowId": "11111111-1111-1111-1111-111111111111", "enabled": true},
    {"workflowId": "22222222-2222-2222-2222-222222222222", "enabled": false}
  ]
}
```

The IDs above are placeholders, not deployable FlowAdmin configuration. Use Dataverse `workflowid`, which persists across imports; do not use display names, Flow API IDs or `workflowidunique`. [Microsoft cloud-flow code reference](https://learn.microsoft.com/en-us/power-automate/manage-flows-with-code).

## Rules

- The manifest is required, including for solutions with no cloud flows. There is no default activation policy.
- Version must be 1; solution must match the requested solution; IDs must be lowercase GUIDs and `enabled` must be a JSON boolean.
- Every definition-type cloud flow in the solution must appear exactly once. Missing, duplicate and foreign IDs fail before C3 writes variables or flow states.
- Maximum 100 entries is an input bound, **not** a tested throughput or timeout guarantee. Inventory requests ask for 101 rows and reject oversized or paginated results. Both OData and FetchXML paging indications are checked.
- Disabled entries are processed before enabled entries. Each phase is serial and preserves manifest order. A failed state update blocks every later state update, including subsequent iterations of the same phase. List child flows before their callers when enabling them. This contract does not infer dependencies or disable order.
- A flow already at its declared state is left untouched. Suspended is a distinct state and is not accepted as Off.
- C3 reads all states again and fails if they do not exactly match the manifest. A partial update is not rolled back automatically.
- Do not run concurrent deployments or edit target states during reconciliation. There is no cross-run lock or transactional state update yet.

## Runtime inputs and evidence

| Flow | Input |
| --- | --- |
| C1 | `text_2`: JSON manifest |
| C2 | `text_3`: JSON manifest, supplied by C1 |
| C3 | `text_2`: JSON manifest, supplied by C1 or an explicit caller |
| C2 | `text_4`: release-artifact descriptor, supplied by C1 |

C1 parses the manifest once and passes the same serialized object to both children. For configuration-only runs (`RunImport=false`, `RunPostImport=true`), it validates against the target inventory, allowing DEV to contain unreleased flows; C1 skips Export, so this run creates no ZIP or release sidecars. Import and export-only runs validate against DEV. C2 independently validates against DEV; C3 validates against the target. For an export run, C1 inspects the managed ZIP and creates a release descriptor, then archives the ZIP, activation manifest and descriptor as `<ZIP name>`, `<ZIP name>.activation.json` and `<ZIP name>.release.json`. Failure to archive either sidecar fails Export and prevents Import. C2 requires the descriptor in `text_4` and checks the exact archived ZIP and manifest against it before submitting the verified ZIP bytes to Dataverse.

This change is deliberately incompatible with old callers that omit the manifest. Update C2/C3 and C1 together during a controlled rollout; avoid invoking the old parent against the new children. Committed `pipeline/definitions/` files remain the historical deployed snapshot until an actual deployment refreshes them. `python3 -m pipeline.deploy --dry-run` produces candidate definitions in a temporary directory.

## Artifact verification and import gate

[The verifier guide](../docs/alm/artifact-verifier.md) has local commands, package-format limits and the current bridge status.

C1 and C2 call the local artifact-verifier service through an optional HTTPS endpoint. When the endpoint is unset, both actions fail closed; C1 cannot archive a release and C2 cannot import. C2 also requires the descriptor in `text_4`; direct invocation without a descriptor is incompatible. The generated flow authorization parameter is a SecureString with an empty default. Runtime credential provisioning and an externally reachable HTTPS verifier are not configured, so the hosted C1/C2 verification path is not enabled.

The verifier hashes the exact ZIP bytes and the canonicalized activation-manifest JSON, checks the solution unique name/version and managed flag, and compares the manifest workflow IDs with the cloud-flow inventory in the package. The descriptor records those hashes and identifiers. Its metadata parser supports the XML solution layout with `Workflows/<name>-<GUID>.json`, corresponding `.json.data.xml` workflow metadata or equivalent mappings in `Customizations.xml`, and type-29 root-component references. It rejects unknown `Workflows/` file types, `modernflows/` packages, malformed XML/JSON, unsafe ZIP paths and unsupported encodings. Other solution package layouts fail closed and require explicit parser support.

The descriptor is an unkeyed integrity record. It detects a changed ZIP or manifest against a trusted descriptor, but it does not authenticate the descriptor itself; an actor who can replace both the ZIP and its descriptor can recompute the pair. Promotion therefore needs separately protected descriptor storage or a signing/trust mechanism before it can claim adversarial tamper resistance. Package inspection also does not test flow execution, connections, import-time activation, or target state.

Cloud-flow imports remain blocked pending isolated import-time activation qualification: C1/C2 reject source or target inventories containing definition-type cloud flows. The separate local release runner can import only a flowless managed solution into a validated isolated target, with an explicit `--apply`, `--exclusive-window`, and durable `--log`. That path is an authenticated Dataverse mutation and has not been runtime-qualified here. Do not interpret static checks or offline tests as Power Automate runtime evidence.

`PublishWorkflows` controls classic Dataverse workflows, not cloud flows. Newly imported cloud flows may activate based on exported state and connection bindings; existing flows can also be affected by import. Flipping that parameter does not make C3 the first activation point. [Code reference](https://learn.microsoft.com/en-us/power-automate/manage-flows-with-code), [import behavior](https://learn.microsoft.com/en-us/power-automate/import-flow-solution).

## Validation and rollout

The local suite executes the generated activation decisions against a simulated Dataverse inventory and tests missing/malformed policies, coverage, duplicate IDs, state ordering, idempotence, write failure, readback mismatch and truncated inventories. Artifact tests cover managed ZIP parsing, hashes, descriptor binding and malformed/unsupported package cases. This is not a Power Automate runtime emulator. The connector definition validator is an additional static check; neither replaces isolated TEST runs.

See [integration readiness](../docs/alm/platform-integration.md) for the baseline, module boundaries, remaining rollout gates and acceptance procedure. Do not apply a policy inferred from FlowError's stale workflow-state manifest.

## Power Automate schema compatibility

TEST activation on October 1 proved that connector-backed Parse JSON actions reject `pattern`/`patternProperties`. Runtime schemas omit these properties while retaining type, required, enum, coverage and other supported constraints. Canonical schemas remain strict for offline inspection. Runtime policy IDs still must exactly match the lowercase GUIDs returned by Dataverse; release descriptors are checked again by the full offline verifier. A static connector validator had accepted the unsupported schema, so the isolated deployment was necessary.
