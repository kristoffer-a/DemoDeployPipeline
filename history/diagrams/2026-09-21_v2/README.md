# ALM diagrams — revision 2

Open [power-platform-alm-v2.drawio](power-platform-alm-v2.drawio) in draw.io Desktop, or use **File → Open From → Device** in the browser editor. The file contains three editable pages:

1. **Solution definition** — a clean boundary view of the Power Platform solution package, target connections, Microsoft Entra groups and identities, and SharePoint sites, lists and role groups.
2. **Solution strategy** — independent business solutions across the three shared Dev / Test / Prod environments, including stage-specific groups and resource mappings.
3. **Deployment pipeline** — the manual release sequence, Test decision, release approval, production verification and recovery path.

Each page also has a PNG preview and a scalable SVG. Shapes and text are native draw.io objects; card labels are attached to their shapes and connectors are attached to their endpoints. Save edits in the `.drawio` file and export new previews from the editor.

The first revision is preserved in the parent folder. This revision focuses on explaining the agreed design; the earlier research note remains the supporting rationale.

`build_diagrams.py` generates the original revision-2 `.drawio` and SVG files using `drawing.py`. Rerunning it overwrites those generated files, so do not run it over a manually edited master. PNG previews are rendered separately.
