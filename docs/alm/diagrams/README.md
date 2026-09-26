# ALM pipeline diagrams

**Current: `alm-pipeline.drawio`** — open in draw.io desktop and edit it directly. 6 pages: release path, architecture, C1 run, C2 + C3, settings, roadmap.

## Which version does it show?

Every page has a grey stamp top right, e.g. *Matches ALMPipeline 1.0.0.0 · Demo 1.0.0.0 · pipeline/ code @ 9f20d8d*. The stamp must always match what is deployed.

| Diagram | Matches | Where |
|---|---|---|
| `alm-pipeline.drawio` (current) | ALMPipeline 1.0.0.0, pipeline/ @ 9f20d8d | this folder |
| overview + full-detail variants | ALMPipeline 1.0.0.0 | `history/diagrams/2026-09-24_ALMPipeline-1.0.0.0/` |
| Mermaid drafts | pre-draw.io | `history/diagrams/2026-09-24_mermaid-drafts/` |

## When the pipeline changes

1. Copy `alm-pipeline.drawio` to `history/diagrams/<date>_ALMPipeline-<old version>/`.
2. Change `pipeline/` → `python3 -m pytest pipeline/tests -q` → `python3 -m pipeline.deploy`.
3. Update the diagram and its stamp (new version + commit), then commit both together.
