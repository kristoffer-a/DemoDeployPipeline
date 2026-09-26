# ALM ability discovery and readiness — 2026-09-16

## Current-work summary

Build the accepted SharePoint ADMIN/DEV/TEST foundation and DEV Demo canvas app/flow, then prove Dataverse connector deployment from ADMIN. Search mode: abilities. Stable core only; no Power Pages, Dataverse data migration, new pipeline host or unrelated diagnostics. User authorized skill installation, spec update and subsequent implementation. Defaults and account now confirmed.

Paths below use `HUB` = `C:/Users/KristofferAllåker/Development/Work/Internal/power-platform-skill`, `BUNDLE` = `C:/Users/KristofferAllåker/Development/Work/Customer/Axfood/AdminEnv/.tooling/power-platform-skills-a804d33267c973314e21f56827e0743ee3f1e690`, `SKILLS` = `C:/Users/KristofferAllåker/.codex/skills`. These are explicit path abbreviations, not shell environment variables.

## Relevant now

| Ability | Exact source | Role and fit | Prerequisites | Effects | Maturity/limitations |
| --- | --- | --- | --- | --- | --- |
| Dataverse connection | `HUB/sources/microsoft-dataverse-skills/.github/plugins/dataverse/skills/dv-connect/SKILL.md`; installed `SKILLS/dv-connect/SKILL.md` | Target identity/auth setup | Approved account and explicit org URL | Local auth/config; optional MCP registration | Installed; local PAC token expired. Do not execute consent/allowlist changes automatically. Browser path remains usable. |
| Dataverse solution lifecycle | `HUB/sources/microsoft-dataverse-skills/.github/plugins/dataverse/skills/dv-solution/SKILL.md`; installed `SKILLS/dv-solution/SKILL.md` | Publisher, Demo, export/import verification | Target access and supported SDK/PAC/API | Solution writes and exports | Installed. Validate snippets against actual SDK; ADMIN runtime remains Dataverse connector. |

## Conditional or later

| Ability | Exact source | Role and fit | Prerequisites | Effects | Maturity/limitations |
| --- | --- | --- | --- | --- | --- |
| Canvas authoring | `BUNDLE/plugins/canvas-apps/skills/canvas-app/SKILL.md`; connection entry `BUNDLE/plugins/canvas-apps/skills/configure-canvas-mcp/SKILL.md` | Task 4 app and later ADMIN UI | Canvas MCP, live Studio/coauthoring, .NET 10, real data source | Sync/edit/compile canvas YAML | Both installed; full references/agents preserved. No live MCP tools yet. Does not add data sources. Keep gallery scope; no generated extra screens/features. |
| Flow construction | `BUNDLE/plugins/power-automate/skills/build-flow/SKILL.md`; setup `BUNDLE/plugins/power-automate/skills/setup/SKILL.md` | Task 5 and later deployment flows | Node, Azure CLI auth, FlowAgent, existing connections | Creates/edits cloud flows | Installed build-flow + power-automate-setup. Server configured but not loaded/authenticated; Azure CLI 2.90.0 installed and version verified on 2026-09-16. Connector metadata and solution wrapping must be verified. |
| Flow lifecycle/testing | `BUNDLE/plugins/power-automate/skills/manage-flows/SKILL.md` | Publish/run and inspect acceptance evidence | Same FlowAgent prerequisites and exact flow/environment IDs | Enables/runs flows | Installed; use only requested demo/deployment tests, no batch tenant changes. |

## Closest exclusions

- Power Pages plan-alm/setup-solution/export/import and pipelines-host skills: wrong workload and host architecture.
- PowerCAT migrate-to-dataverse: contradicts SharePoint datasource requirement. Canvas performance audit and PowerCAT Overflow: unnecessary for the current gallery/dummy flow; no hosted viewer upload authorized by this selection.
- Private repository abilities assess-knowledge-source and knowledge-retrieval-evaluator: catalogue curation/evaluation, not ALM execution. Knowledge-find remains the private repository discovery ability already invoked.
- No exact SharePoint site/list provisioning skill found in this bounded source set. Use supported browser/admin operations plus Microsoft documentation.

## Unresolved discriminator

Live MCP startup/auth and Studio connection remain unverified. This determines whether task 4/5 use the MCP authoring workflow or the supported browser workflow; installed instruction files alone do not establish runtime readiness.

## Discovery trace

- **Wiki ID:** power-platform.
- **Workload domains:** canvas-apps, power-automate; Dataverse via ledger fallback because no workload domain exists.
- **Concept pages:** both `openwiki/domains/{domain}/abilities/plugin-and-skills.md`, reached through WIKI_INDEX, catalogue, domain index and abilities indexes.
- **Fallbacks used:** `knowledge-index/assets.json` narrowed to Microsoft Power Platform/Dataverse/PowerCAT skills for canvas, flow, solution, connection; private lane restricted to internal-plugins and evaluation SKILL.md entries.
- **Exact sources opened:** table entry points; Canvas `references/CreateWorkflow.md`, `skills/add-data-source/SKILL.md`, `.mcp.json`; Power Automate `.mcp.json`; `catalogues/sources/microsoft-power-platform-skills.md`; private curator/evaluator SKILL.md entry points.
- **Material uncertainty:** hub is a local overlay at ab47760178456cfb2d32cbde4d2003bdcfce2742; its source record explicitly does not prove upstream commit membership. Therefore installation used official GitHub instead of asserting the overlay revision was an upstream revision. Downloaded official immutable bundle a804d33267c973314e21f56827e0743ee3f1e690; installed first four skill hashes match. Setup installed explicitly at same revision. Current Canvas server manifest no longer requests prerelease, but tenant/coauthoring compatibility still needs proof.

## Installation and invocation record

Skill-installer helper installed canvas-app, configure-canvas-mcp, build-flow, manage-flows, and power-automate-setup into SKILLS. New skills are available for discovery on the next turn; they can be read by exact path now. Resolve `${PLUGIN_ROOT}` against the corresponding BUNDLE plugin when invoking. Do not discard BUNDLE while this project depends on it.

Project `.codex/config.toml` registers Canvas Authoring (`dnx Microsoft.PowerApps.CanvasAuthoring.McpServer --yes`) and the pinned FlowAgent Node bundle. Config written is not a connection success claim. No credentials were stored. Existing Microsoft Docs/Code Reference and dv skills remain available.

Verification: all five installed SKILL.md hashes match the pinned bundle; project TOML parses and both executable/server paths exist. Independent readiness review found no material spec gaps with explicit BUNDLE routing. FlowAgent passes `node --check`. Treat power-automate-setup as prerequisite guidance only: its recovery instructions target Claude/Copilot configuration and its internal name is `setup`; do not run those repair instructions against this Codex project.

Codex MCP configuration reference: https://learn.chatgpt.com/docs/extend/mcp?surface=cli. Upstream bundle: https://github.com/microsoft/power-platform-skills/tree/a804d33267c973314e21f56827e0743ee3f1e690.


## 2026-09-17 runtime recovery

FlowAgent tools remain unexposed in the current Codex tool list, but the pinned official server is callable through docs/alm/flowagent-mcp-client.mjs using standard stdio MCP. Handshake and 59 input schemas verified (flowagent-tools.json, flowagent-readiness.md). This does not yet prove tenant calls or flow creation. Azure CLI authenticated approved account/tenant; Power Automate resource token acquisition verified without token output. Canvas was built/published through supported Studio UI and passed task-4-review.md.
