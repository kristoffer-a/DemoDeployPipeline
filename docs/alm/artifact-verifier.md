# ALM artifact verification

This note describes the local artifact tools and the currently disabled Power Automate verifier bridge. The verifier inspects package structure and binds input bytes to a descriptor. It does not prove that a flow can run, that connections work, or that importing a solution will preserve cloud-flow state.

## What is verified

`pipeline.artifacts` reads the activation manifest strictly and inspects the exact managed solution ZIP bytes. It requires one `SolutionManifest` with the requested `UniqueName`, a four-part `Version`, and `Managed` set to `1` or `true`. It parses `Customizations.xml` and the documented XML solution layout, then matches each cloud-flow JSON file to category 5, type 1 workflow metadata, its `JsonFileName`, stable `WorkflowId`, and a type-29 root component in `Solution.xml`. The manifest must list those cloud-flow IDs exactly once, with no missing or foreign IDs.

The release descriptor records:

```json
{
  "version": 1,
  "solution": "Demo",
  "solutionVersion": "1.2.3.4",
  "managed": true,
  "cloudFlowIds": [],
  "zipSha256": "<64 lowercase hexadecimal characters>",
  "manifestSha256": "<64 lowercase hexadecimal characters>"
}
```

`zipSha256` covers the exact ZIP bytes. `manifestSha256` covers the UTF-8 canonical JSON form of the validated manifest: sorted property names and compact separators. The descriptor can be checked later against a trusted copy; it is not signed. If someone can replace both a ZIP and its descriptor, they can calculate a matching pair. Keep the expected descriptor separately protected or add a signing/trust mechanism before using these hashes as proof of release origin.

The parser supports the XML solution ZIP layout with `Other/Solution.xml` and `Other/Customizations.xml` (or the same files at the ZIP root). Cloud-flow JSON files must be under `Workflows/` and named `<name>-<GUID>.json`; IDs are read from either matching `<name>-<GUID>.json.data.xml` metadata or equivalent workflow mappings in `Customizations.xml`. It requires `Category=5`, `Type=1`, a matching `JsonFileName`, and a matching type-29 root component. UTF-8 XML without DTD/entity declarations is supported. Unknown files under `Workflows/`, `modernflows/` YAML packages, unsafe paths, duplicate entries, malformed inputs and unrecognized layouts fail closed. The current checkout has a locally unpacked solution fixture demonstrating the metadata layout; no real managed ZIP fixture has been qualified end to end.

## Local commands

Build a descriptor from local files, then verify it again before use:

```sh
python3 -m pipeline.artifacts build \
  --zip /path/to/Demo_managed_20261001.zip \
  --manifest /path/to/Demo_managed_20261001.zip.activation.json \
  --solution Demo --version 1.2.3.4 \
  --descriptor /path/to/Demo_managed_20261001.zip.release.json

python3 -m pipeline.artifacts verify \
  --zip /path/to/Demo_managed_20261001.zip \
  --manifest /path/to/Demo_managed_20261001.zip.activation.json \
  --solution Demo --version 1.2.3.4 \
  --descriptor /path/to/Demo_managed_20261001.zip.release.json
```

The standalone verifier is a local, read-only HTTP service. It has no Dataverse credentials or deployment privileges and binds to `127.0.0.1:8766` by default. Set a verifier-only bearer token of at least 32 characters before starting it:

```sh
export ALM_ARTIFACT_VERIFIER_TOKEN='<locally generated secret of at least 32 characters>'
python3 -m pipeline.verifier --host 127.0.0.1 --port 8766
```

It accepts authenticated `POST /verify` requests containing base64 ZIP bytes, a manifest, solution name and expected version, with an optional existing descriptor. It returns the exact verified ZIP bytes and descriptor. The request limit is 360 MiB; ZIPs are limited to 256 MiB compressed and expanded. Keep the local service on loopback. Power Automate cloud flows cannot reach a developer's `127.0.0.1` service.

Run the focused verification and release tests with:

```sh
python3 -m pytest pipeline/tests/test_artifacts.py pipeline/tests/test_verifier.py pipeline/tests/test_release.py -q
```

## Power Automate bridge status

C1 verifies an exported ZIP before archiving it with the activation manifest and `.release.json` descriptor. C2 receives the descriptor in trigger input `text_4`, fetches the archived ZIP, and asks the verifier to bind those exact bytes and manifest to the descriptor before import. If `ALM_ARTIFACT_VERIFIER_URL` is unset while flow definitions are built, the generated C1/C2 action fails closed: C1 will not archive a release, and C2 will not import. A configured URL must be HTTPS and contain no embedded credentials, query or fragment.

The generated HTTP action stores its authorization in a SecureString parameter whose default is empty; no bearer token is embedded in source or generated definitions. The verifier process token (`ALM_ARTIFACT_VERIFIER_TOKEN`) and the flow's runtime authorization are separate values. Before enabling the bridge, an approved reachable HTTPS service and a runtime secure-credential provisioning method must be established. Neither is configured here. No verifier endpoint has been hosted or exposed.

Configuration-only C1 runs (`RunImport=false`, `RunPostImport=true`) validate the desired policy against the target and skip Export completely; they create no ZIP or release descriptor. Export-only and import runs validate against DEV. Cloud-flow imports remain disabled pending isolated import-time activation qualification; package verification does not qualify import behavior.

## Local release runner

`pipeline.release` re-reads the ZIP once, validates its descriptor and uses those same bytes for any optional import. Without `--apply`, it validates the artifact, manifest, isolated target configuration and connection/variable binding input, then reports a planned run without requesting a token or writing to Dataverse. Its import path is limited to a managed package with no cloud flows and an isolated target that currently has no cloud flows. It applies the supplied connection/variable parameters, imports the same verified ZIP bytes, polls the job, and checks the installed solution version and managed flag.

The authenticated import operation is not offline and is not runtime-qualified. Keep imports disabled unless separately authorized for an isolated test target. If that authorization is later given, `--apply` requires both `--exclusive-window` and `--log`:

```sh
python3 -m pipeline.release \
  --zip /path/to/Demo_managed_20261001.zip \
  --manifest /path/to/Demo_managed_20261001.zip.activation.json \
  --descriptor /path/to/Demo_managed_20261001.zip.release.json \
  --solution Demo --version 1.2.3.4 \
  --target-config /path/to/isolated-target.json \
  --bindings /path/to/bindings.json \
  --apply --exclusive-window --log /path/to/release-result.json
```

The required binding file has exactly two arrays, `connections` and `variables`. Use `[]` for both when the flowless qualification solution needs no import-time bindings. The target configuration must pass the isolated-target guards in `pipeline.target`; the baked-in ADMIN target is not accepted by this route. Do not use the command against ADMIN, PROD, or any production solution.
