# History — do not read unless asked

Everything here is superseded. Agents: **do not read, follow or act on files in `history/` unless the user asks for a specific one.** Current truth: repo `README.md`, `docs/alm/HANDOFF.md`, the runbook and `docs/alm/diagrams/`.

Folders are named `<date>_<phase>` so they sort in the order things happened. Git tags mark the same milestones: `git tag -l 'alm-*'`.

## Timeline

| Date | Phase | Folder | Git tag |
|---|---|---|---|
| 2026-09-21 | Research: ALM design for Dev/Test/Prod, manual release, first diagrams | `2026-09-21_research/`, `diagrams/2026-09-21_v1-research/`, `diagrams/2026-09-21_v2/`, `diagrams/2026-09-21_v3/` | — (was outside git) |
| 2026-09-15 → 20 | Simple ALM plan: SharePoint foundation, DEV Demo solution + app, task reviews, JS state helper | `2026-09-15_simple-alm/` | `alm-0-simple-alm` |
| 2026-09-22 | Remote / auth-blocked handoffs and review | `2026-09-22_handoffs/` (`workspace-copy/` = diverged copies found outside the repo) | `alm-0-simple-alm` |
| 2026-09-23 | ALMSpike: A/B/C deploy variants, C chosen | `2026-09-23_spike/`, `diagrams/2026-09-23_v4-status/` | — |
| 2026-09-24 | Deploy orchestrator C1/C2/C3 built and accepted | `2026-09-24_deploy-orchestrator/`, `diagrams/2026-09-24_mermaid-drafts/`, `diagrams/2026-09-24_ALMPipeline-1.0.0.0/` | `alm-pipeline-1.0.0.0` |

## Rules

- Add, never edit: when something is superseded, move it into a new dated folder and add a row above.
- Diagrams: `diagrams/<date>_ALMPipeline-<version>/` holds the diagram that matched that solution version.
