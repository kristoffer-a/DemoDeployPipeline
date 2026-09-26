# Handoff — current state (updated 2026-09-26)

Branch `main` (tag `alm-pipeline-1.0.0.0`). Work in your own worktree + branch (see `AGENTS.md`). How to operate it: `docs/alm/deploy-orchestrator-runbook.md`. Picture: `docs/alm/diagrams/alm-pipeline.drawio`.
Older handoffs, plans and reviews are in `history/` — do not read them unless asked.

## Live now

| Environment | Solution | What is in it |
|---|---|---|
| ADMIN | ALMPipeline 1.0.0.0, unmanaged | C1 Deploy, C2 Import, C3 Post-import (on); ALM Setup - SharePoint config (off); 2 connection references |
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

1. **TEST mapping may still be the test-6 value.** The last C1 run was acceptance test 6 (ConnectionId `shared-sharepointonl-WRONG0000`). Run `python3 -m pipeline.sp_setup readback` + the setup flow and confirm `dev_SharePoint` → `shared-sharepointonl-0f567e53` before the next real deploy.
2. **TEST `dev_ProductsList` is a placeholder** (`00000000-…`). Create the TEST Products list, then `python3 -m pipeline.sp_setup variable dev_ProductsList=<id>`, run C1, and test the app as a target user.

## Open — code fixes (from review 2026-09-25)

3. `pipeline/flowapi.py` checks the tenant but not the account before getting a token. Also check the account.
4. `pipeline/deploy.py` finds flows by display name across all of ADMIN. Scope the lookup to solution ALMPipeline and fail on duplicates.

## Open — design

5. **Release to PROD with the same ZIP** (diagram page 1, steps ③ ④): version in ZIP name, C1 option "deploy archived ZIP" (skip export), approval step, PROD rows in the 3 lists.
6. **Solution versions never change.** ALMPipeline and Demo are both 1.0.0.0. Bump versions on each release, so ZIPs, run logs and diagrams can name the version.
7. Future children: C5 SharePoint deploy, C6 security groups, C4 share app (needs a Power Apps for Admins connection, `docs/alm/c4-share-spike.md`).
8. Service account to replace kriall076.

## Tooling

- ChatGPT/Codex uses `.codex/config.example.toml` + `docs/alm/flowagent-*.mjs` (tenant guard). The example still has Windows paths and pins DEV as default environment; adjust per machine. The `.mjs` files are JavaScript (workspace rule prefers TypeScript) — convert if they are changed.
