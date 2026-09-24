# ALM pipeline diagrams

Mermaid sources. Open in draw.io (Arrange > Insert > Advanced > Mermaid) or any Mermaid viewer.
Change loop: mark a change on a diagram → update `pipeline/` → `python3 -m pytest pipeline/tests -q` → `python3 -m pipeline.deploy` → update the diagram here.

| File | Shows |
|---|---|
| 01-architecture.mmd | environments, flows, SharePoint lists, connections |
| 02-c1-run-flow.mmd | C1 stages, switches, failure paths, log |
| 03-sequence-parent-children.mmd | C1 ↔ C2 ↔ C3 calls, inputs, reply contract |
| 04-config-model.mmd | ALMConfig / ALMConnections / ALMVariables and how they bind |
| 05-roadmap-children.mmd | proposed future children C4–C6 and their switches (not built) |
| 06-c2-c3-internals.mmd | step-by-step C2 and C3 |
