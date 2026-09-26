# Power Platform ALM design

An evidence-based refinement of the proposed customer setup: three shared Dev / Test / Prod environments, SharePoint business data, Dataverse for solution metadata, no Managed Environments, and initially no hosted Git platform.

## Deliverables

- [Design review and Microsoft sources](docs/power-platform-alm-research.md): validation, corrections, revised solution definition, manual release checklist, recovery guidance, and remaining decisions.
- [Editable diagrams — two pages](diagrams/power-platform-alm.drawio): native shapes, editable text, and attached connectors.
- [Environment model — PNG](diagrams/01-environment-model.png) / [SVG](diagrams/01-environment-model.svg).
- [Solution boundary — PNG](diagrams/02-solution-boundary.png) / [SVG](diagrams/02-solution-boundary.svg).

## Edit the diagrams

Open `diagrams/power-platform-alm.drawio` in draw.io Desktop, or use [the draw.io browser editor](https://app.diagrams.net/) and choose **File → Open From → Device**. The file contains two page tabs. Every box, label, and connector is editable; it is not a flattened image. Save your edited copy locally. See [draw.io's opening instructions](https://www.drawio.com/docs/manual/open-diagram-file/).

Use the `.drawio` file as the editable master. PNG and SVG files are presentation previews. After manual edits, export fresh previews from draw.io. `diagrams/build_diagrams.py` recreates the original draw.io and SVG files and **will overwrite manual edits**, so do not rerun it on an edited master. It does not regenerate PNGs.

## Read the diagrams

**Page 1:** Columns represent lifecycle stages. SharePoint resources are shown under their assigned stage but remain outside Power Platform environments. Environment admission, business audience sharing, solution packages, and external data permissions are distinct. The release strip promotes the same tested managed artifact to Prod.

**Page 2:** The blue boundary contains solution components. Actual connections, credentials, SharePoint resources, and security grants remain outside it. Canvas-to-SharePoint access uses the user's OAuth connection. Flow-to-SharePoint access binds through a connection reference and, in the proposed setup, uses a service-user connection. Dashed lines supply configuration; solid lines show runtime calls or connection bindings.

The proposed dependency policy is strict for other business solutions, with unavoidable external and platform dependencies documented. The research note describes how any future exception would need an explicit design decision.

## Validation status

Microsoft documentation was reviewed on 21 September 2026. Both PNG previews were rendered from the SVGs and visually inspected. The draw.io XML was checked for well-formedness, unique component IDs, and valid connector endpoints. No customer environment, permissions, licenses, deployment, or recovery was tested. A representative end-to-end pilot remains necessary before adopting the process.
