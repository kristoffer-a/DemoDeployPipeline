# Handoff — current state (updated 2026-10-01)

## Integration candidate — qualified paths in isolated TEST only

Branch `codex/flowadmin-deployment-contract`, based on `4883edd`. October 1 source adds ZIP inspection, release descriptors, a local authenticated verifier, explicit isolated targets, controlled rollout, independent bootstrap, qualification fixtures, recovery documentation and offline CI. User decision: prepare the verifier locally and keep imports disabled. The verifier is not hosted; cloud-flow imports remain blocked.

Candidate C3 passed isolated TEST coverage, state ordering, idempotence, injected write failure and readback mismatch checks. A fixed-input C1 clone passed configuration-only orchestration and logging, plus failed-policy logging. See [runtime evidence](qualification-2026-10-01.md), [integration gates](platform-integration.md), [contract](../../contracts/README.md) and [verifier](artifact-verifier.md). These tests do not qualify ZIP imports or ADMIN deployment. Historical `pipeline/definitions/` are preserved.

The missing TEST Products list is now `9ca71bdc-8192-4321-85ce-f29ac9d3a7d8`; schema readback matches DEV. ALM-Admin's Demo TEST mapping and TEST environment value now use that ID. Demo `RunImport=false` and ADMIN direct C2 is stopped. The setup helper's original definition and stopped state were restored. ADMIN C1/C2/C3 definitions otherwise remain on their existing release.

Dedicated resources in TEST: `almqualification` publisher, `ALMQualification` 1.1.0.0, inert fixtures, qualification lists and logging library, connection `shared-commondataser-3dbb75d1`. Completed harnesses and fault clones are stopped; no resources deleted. No ZIP imports or source merges were performed during qualification. The non-diagram source is prepared for publication through a reviewed PR. Diagrams are outside scope and existing diagram changes are preserved.

Browser app acceptance is waiting for fresh interactive sign-in. FlowError is clean on local main `08798c7`, with 48 tests and 15 static checks passing. Its documented large-load/Poll limits remain. Additive operational-readiness tooling is under `integrations/flowerror-readiness/`. Preserve both FlowError checkouts and ALM's SharePoint worktree.

## Deployed baseline

Branch `main` (tag `alm-pipeline-1.0.0.0`). Work in your own worktree + branch (see `AGENTS.md`). How to operate it: `docs/alm/deploy-orchestrator-runbook.md`. Picture: `docs/alm/diagrams/alm-pipeline.drawio`.
Older handoffs, plans and reviews are in `history/` — do not read them unless asked.

## Deployed baseline and October 1 changes

| Environment | Solution | What is in it |
|---|---|---|
| ADMIN | ALMPipeline 1.0.0.0, unmanaged | C1 Deploy and C3 Post-import (on); C2 Import (off by user decision Oct 1); ALM Setup - SharePoint config (off); 2 connection references |
| DEV | Demo 1.0.0.0, unmanaged | Demo Products canvas app, dev_SharePointSite, dev_ProductsList, dev_SharePoint |
| TEST | Demo 1.0.0.0, managed | same, imported by C2 |

- Flows are generated from `pipeline/` (Python) and deployed with `python3 -m pipeline.deploy`. 59 tests pass. Live definitions match the committed ones (checked 2026-09-25).
- Settings: ALM-Admin SharePoint lists `ALMConfig`, `ALMConnections`, `ALMVariables`. ZIPs in `Solutions/`, run logs in `DeploymentLogs/`.
- Acceptance tests 1–6 passed 2026-09-24 (runbook table).

## Rules in force

- Tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac` only. Accounts kriall076 (default, signed in in Chrome) or bosso (test user, same permissions). Service account later.
- Commit only when the user asks.
- Don't touch FlowAdmin* solutions, publisher M365/ms365, solution `Development`, or SharePoint lists Environments / Settings / Flow* (another project). Failed ALM runs in ADMIN raise FlowAdmin-Monitoring incidents + Teams cards: warn before failing on purpose.
- Diagrams: keep the version stamp in sync; snapshot old versions to `history/diagrams/` (see diagrams README).

## Open — check first

1. **TEST mapping resolved by live UI read, September 30.** `dev_SharePoint` maps to `shared-sharepointonl-0f567e53`; connection authentication was not retested.
2. **Legacy Test* columns confirmed present September 30:** TestPowerPlatformUrl and TestSharePointUrl. Leave them until explicitly authorized cleanup.
3. **TEST Products provisioned and mapped October 1.** Both stored mapping and target value are `9ca71bdc-8192-4321-85ce-f29ac9d3a7d8`. Target-user app acceptance remains pending fresh browser sign-in. Do not enable imports to perform that check.

## Code fixes — implemented locally, not deployed

4. `pipeline/flowapi.py` now checks the tenant, interactive-account type and kriall076/bosso allowlist before token acquisition; regression-tested.
5. `pipeline/deploy.py` now scopes lookup to ALMPipeline and definition-type cloud flows, rejects duplicates and sends the solution header on updates. Failed authentication no longer overwrites deployed definition snapshots.

## Open — design

6. **Release to PROD with the same ZIP** (diagram page 1, steps ③ ④): version in ZIP name, C1 option "deploy archived ZIP" (skip export), approval step, PROD rows in the 3 lists.
7. **Solution versions never change.** ALMPipeline and Demo are both 1.0.0.0. Bump versions on each release, so ZIPs, run logs and diagrams can name the version.
8. **C5 SharePoint metadata deployment is proposed, not implemented.** Opt in per deployment: copy DEV metadata to an empty target; report differences and offer a force push for an existing target. Define metadata scope before implementation. There is no RunSharePoint switch or C5 flow. C4 app sharing and C6 security groups remain future work.
9. Service account to replace kriall076.

## Tooling

- ChatGPT/Codex uses `.codex/config.example.toml` + `docs/alm/flowagent-*.mjs` (tenant guard). The example still has Windows paths and pins DEV as default environment; adjust per machine. Its tenant guard (`flowagent-auth-policy.mjs`) pins **bosso**, so Codex signs in as bosso while Claude uses kriall076; both are approved. The `.mjs` files are JavaScript (workspace rule prefers TypeScript) — convert if they are changed.
