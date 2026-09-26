# DemoDeployPipeline

Power Platform ALM for the Demo solution: one click in ADMIN exports a managed solution from DEV, archives the ZIP in SharePoint, imports it into TEST (later PROD, same ZIP) and sets connections and variables. The runtime is Power Automate; the flows are built and deployed from Python in `pipeline/`.

## Start here

Agents: follow `AGENTS.md` (Claude Code and ChatGPT/Codex). Each agent works in its own worktree and branch.

1. `docs/alm/HANDOFF.md` — current state, rules, open items.
2. `docs/alm/deploy-orchestrator-runbook.md` — configure, deploy, run, verify.
3. `docs/alm/diagrams/alm-pipeline.drawio` — the picture (open in draw.io desktop).
4. `docs/superpowers/specs/2026-09-23-deploy-orchestrator-design.md` — design decisions.

`history/` holds superseded plans, handoffs, reviews, the spike and old diagrams. **Do not read it unless the user asks.**

## Layout

| Path | What |
|---|---|
| `pipeline/` | flow definitions as code, deploy + setup scripts, tests |
| `pipeline/definitions/` | generated flow JSON (committed; matches live) |
| `docs/alm/` | handoff, runbook, C4 research, diagrams |
| `history/` | archive, not for active use (dated folders + `alm-*` git tags) |
| `.codex/`, `docs/alm/flowagent-*` | ChatGPT/Codex setup (copy `config.example.toml` to `config.toml`) |

## Security boundary

- Tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac` only. Every script stops on another tenant.
- Accounts: `kriall076@7xpydh.onmicrosoft.com` (default, signed in in Chrome) or `bosso@7xpydh.onmicrosoft.com` (test user, same tenant and permissions). Service account later.
- Do not copy Azure, MSAL, browser, PAC, connection or token caches between machines. Authenticate fresh on each machine.
