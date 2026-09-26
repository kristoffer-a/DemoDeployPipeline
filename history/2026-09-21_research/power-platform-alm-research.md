# Power Platform ALM with SharePoint: design review

Research date: 21 September 2026. Sources are Microsoft documentation; recommendations and architectural inferences are explicitly distinguished from documented platform behavior. No tenant configuration, licensing assignments, or deployments were inspected or tested.

## Confirmed design constraints

- Exactly three shared lifecycle environments: Dev, Test, and Prod. Several independent business solutions coexist in each.
- SharePoint stores business data. Dataverse databases for platform/solution metadata are acceptable; this was clarified during the review.
- Managed Environments are not enabled. A Git hosting platform is initially unavailable.
- Licensed service-user accounts are scarce. Existing SharePoint connector authentication constraints remain part of the design.

**Assessment:** This is a workable starting architecture. Its strongest ideas are lifecycle separation, business-focused deployment units, and group-based access. The important corrections concern environment membership, the distinction between packaging and security, SharePoint runtime identities, and SharePoint schema delivery.

## Platform facts and implications

### 1. Keep Dataverse metadata; keep SharePoint business data

Microsoft states that environments participating in solution-based ALM require a Dataverse database, which stores solution artifacts. That does not require moving the application's SharePoint business records into Dataverse. The clarified design satisfies this prerequisite. [ALM overview](https://learn.microsoft.com/en-us/power-platform/alm/overview-alm)

Use **unmanaged solutions in Dev** and export **managed solutions to Test and Prod**. Microsoft treats the managed export as a build artifact and recommends managed deployment downstream. A managed solution cannot be imported back into the environment containing its originating unmanaged solution. [Solution concepts](https://learn.microsoft.com/en-us/power-platform/alm/solution-concepts-alm)

Managed solutions and Managed Environments are different concepts: the latter is an optional set of premium administration capabilities. The ordinary solution import interface accepts a package from a device. **Inference:** Manual managed-solution deployment fits the stated constraints; enabling Managed Environments is not a prerequisite for this workflow. [Managed Environments overview](https://learn.microsoft.com/en-us/power-platform/admin/managed-environment-overview), [Import solutions](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/import-update-export-solutions)

**Recommendation:** Use suitable shared sandbox environments for Dev and Test and a production environment for Prod. “Dev” here is a lifecycle label, not a request for a personal Developer-type environment. Default and Developer environments cannot have an environment security group assigned. [ALM environment basics](https://learn.microsoft.com/en-us/power-platform/alm/basics-alm), [Environment access control](https://learn.microsoft.com/en-us/power-platform/admin/control-user-access)

### 2. Shared environments are feasible; solutions do not isolate makers or runtime privileges

Microsoft documents multiple solutions in one development environment. It warns against including the same unmanaged component in several solutions and recommends a consistent publisher. All unmanaged solutions share one unmanaged layer, while managed components can acquire layers from other solutions. [Organize solutions](https://learn.microsoft.com/en-us/power-platform/alm/organize-solutions), [Solution layers](https://learn.microsoft.com/en-us/power-platform/alm/solution-layers-alm)

**Recommendation:** Keep one owning solution for each custom component, a stable publisher/prefix, named business and technical owners, and an explicit release schedule per solution. Coordinate edits in shared Dev; a solution folder does not prevent another sufficiently privileged maker from changing its components. Keep Test and Prod free of routine direct edits and inspect for accidental unmanaged layers before release.

**Inference:** A solution is a packaging/dependency boundary, not an authorization boundary. Microsoft defines environments as security boundaries and separates app sharing, security roles, and connector credentials. Therefore “share a solution with a group” should become “share each app and applicable flow with the relevant group, and grant required data access separately.” [Dataverse and Power Platform security](https://learn.microsoft.com/en-us/power-platform/admin/wp-security)

### 3. Correct the environment-group gate in image 1

The original admin/service-only environment groups would exclude ordinary users. Current Microsoft documentation explicitly says that a canvas app can be shared outside its environment security group, but the recipient must belong to that group to run it. Group membership alone does not supply all necessary roles or licenses. [Environment access control](https://learn.microsoft.com/en-us/power-platform/admin/control-user-access)

**Recommended access model:**

| Control | Dev | Test | Prod |
|---|---|---|---|
| Environment admission group | Makers, authorized operators, required service users | Testers, release operators, required service users | Business users, production operators, required service users |
| App audience groups | Maker/test audience per business solution | UAT audience per solution | Business audience per solution |
| Maker/admin privileges | Named makers and administrators | Restricted deployment/support personnel | Restricted deployment/support personnel |
| SharePoint permissions | Development data only | Test data only | Production business data |

Environment admission is not an administrator grant. Use separate role assignments for administration and creation. Canvas apps can be shared with Microsoft Entra security groups. [Share a canvas app](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/share-app)

**Recommendation:** Use stage-specific app groups, such as `SG-Claims-Test-Users` and `SG-Claims-Prod-Users`. Reuse these as membership sources for relevant SharePoint groups where appropriate, rather than maintaining unrelated user lists. SharePoint supports placing security groups in its permission groups; group-connected team sites have additional Microsoft 365 group conventions. [Modern SharePoint permissions](https://learn.microsoft.com/en-us/sharepoint/modern-experience-sharing-permissions)

SharePoint groups can implement different site/content permission levels. Permissions are additive: adding a user to a restrictive group does not cancel wider access granted elsewhere. **Recommendation:** Review inherited access, Microsoft 365 membership, direct grants, and sharing links when implementing segmented security. [Customize SharePoint permissions](https://learn.microsoft.com/en-us/sharepoint/customize-sharepoint-site-permissions)

### 4. Draw canvas and flow connections differently in image 2

For cloud flows, a connection reference is a solution component that points to an actual connection supplied in the target environment. Microsoft specifically limits canvas-app connection-reference use to implicitly shared, non-OAuth connections; SharePoint OAuth is not this case. Flow designers can reuse references from other solutions, so explicitly select a reference owned by the intended solution. [Connection references](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/create-connection-reference)

For the standard SharePoint connector, the documented connection is not shareable with canvas-app recipients: each user establishes a connection. The current connector reference does not document an app-only service-principal authentication option. **Implication:** A service user's SharePoint connection does not automatically become the identity used by everybody running a canvas app. [SharePoint connector](https://learn.microsoft.com/en-us/connectors/sharepointonline/)

Show these two runtime paths:

- **Direct app access:** canvas app → signed-in user's SharePoint connection → SharePoint permissions for that user.
- **Flow access:** solution flow → solution connection reference → target connection → SharePoint permissions for the connection identity. An app may call this flow.

The app and flow also read environment variables for destination/configuration. Connections and credentials stay outside the solution package. Sharing an app and supplying access to its dependent resources are separate concerns. [Share app resources](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/share-app-resources)

For instant flows, run-only access permits execution without editing. The owner can choose an existing connection or require the caller's connection; the latter acts with the caller's data access. Co-owners can edit flow logic and manage ownership. [Share a cloud flow](https://learn.microsoft.com/en-us/power-automate/create-team-flows)

**Security inference:** A flow using a service-user connection can expose operations that exceed the caller's direct SharePoint rights. App filters and hidden buttons cannot secure that route. Validate the actual caller's authorization inside the trusted execution path, constrain allowable destinations and record operations, and do not trust an email address or privilege flag supplied by the canvas app. Test unauthorized calls and parameter tampering. Keep run-only users separate from flow co-owners.

### 5. Allocate scarce service identities by privilege boundary

Flow ownership and connector authentication are separate. Power Automate supports service-principal-owned flows, including solution flows, subject to licensing/request rules. This does not change how an underlying SharePoint connection authenticates. **Recommendation:** Preserve the current service-user arrangement initially, while recording both the flow owner and connection owner; consider SPN ownership separately if operationally useful. [Service-principal-owned flows](https://learn.microsoft.com/en-us/power-automate/service-principal-support)

**Recommendations under account scarcity:**

1. Prioritize separation between Prod and non-Prod service identities. Non-Prod accounts should have no production SharePoint grants.
2. Within Prod, separate genuinely different security domains where accounts permit it. Reuse only where privilege requirements and business ownership are compatible.
3. Several connections signed in as the same account do not narrow that account's SharePoint rights. Treat all sites reachable by it as the possible impact area of a faulty or abused flow.
4. Record least-privilege site/list grants, connection purpose, approved flows, account custodian, recovery contact, and reauthentication procedure. Avoid shared credentials for everyday human development.
5. Validate license entitlements against actual connectors, triggers and invocation patterns. Metadata Dataverse, service ownership, and user execution are distinct questions; this review is not a tenant license audit.

### 6. Give SharePoint its own delivery track

Canvas SharePoint ALM needs separate Site and List environment variables. Corresponding columns need matching display/logical names and metadata; creating similarly named lists manually can leave incompatible internal identifiers. **Recommendation:** Establish a repeatable list-provisioning procedure and prove it with the customer's real column types before scaling the pattern. [Environment variables](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/environmentvariables)

Existing apps do not automatically adopt data-source environment variables: Microsoft instructs makers to remove and re-add the data source through the environment-variable configuration. Referencing a variable in another solution creates a dependency. [Canvas data-source environment variables](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/environmentvariables-data-source-canvas-apps)

Microsoft also documents SharePoint ALM reference-update issues and browser caching of variable values. **Recommendation:** After import, test actual reads and writes against the target site/list using an ordinary user and a fresh session; a successful import or apparently correct designer screen is insufficient evidence. [Troubleshoot data-source references](https://learn.microsoft.com/en-us/troubleshoot/power-platform/dataverse/working-with-solutions/dataverse-environment-variables)

**Recommendation:** Keep independent Dev, Test, and Prod SharePoint sites/lists, even though all live in the same Microsoft 365 tenant. Replace “Dev/test? Site” with an unambiguous Test destination. Version the schema/provisioning instructions, seed data, access matrix, and migrations alongside every release. Avoid production personal data in tests unless an approved handling procedure exists. SharePoint schema, content, groups, and permissions require their own deployment/verification steps outside the Power Platform package.

**Scope exceptions to check:** SharePoint-customized list forms cannot be moved to another list/environment. Also, the SharePoint Automate menu only lists selected-item/file flows from the default environment. Those experiences need a separate design decision if present; standalone canvas apps and ordinary triggers avoid conflating them with this package pattern. [SharePoint connector limitations](https://learn.microsoft.com/en-us/connectors/sharepointonline/)

## Revised solution definition

> A business solution is an independently owned and released set of components serving a bounded business capability. Its Power Platform solution contains its custom solution-aware components, configuration definitions, and flow connection references. Each custom component has one owning solution. Cross-business-solution dependencies are prohibited by default; any approved shared dependency must have a named owner, version contract, deployment order, and impact assessment. Platform dependencies and explicitly documented external resources—including SharePoint sites/lists, identities, runtime connections, and permissions—are allowed and managed through a release manifest. Access is enforced through environment admission, app/flow sharing, and data permissions; the solution package itself does not grant authorization.

This is a **recommended governance policy**, not a platform guarantee. It preserves the intent of “no dependencies outside the solution” while acknowledging unavoidable platform and external-runtime dependencies. A dependency check cannot by itself discover every hard-coded URL, flow ID, or external data contract.

## Initial release process without hosted Git

The following is a **recommended temporary operating procedure**. A controlled artifact library provides traceability, but it does not provide source merging or a complete substitute for source control.

1. **Define:** Record owner, business scope, component inventory, external dependencies, app groups, SharePoint grants, and runtime identities. Reserve a release version and change record.
2. **Build in Dev:** Use the designated unmanaged solution. Agree who edits each app/flow; avoid simultaneous edits. Finish changes and publish before packaging.
3. **Prepare SharePoint:** Apply the versioned Test schema procedure and test data. Check names, internal metadata, permissions, and backward compatibility. Record migration/recovery instructions.
4. **Freeze and export:** Store the unmanaged source export and managed deployment export together with a manifest, change notes, checksum, target variable/connection mappings, schema version, and test plan. Restrict modification of released artifacts. Do not include credentials.
5. **Import into Test:** Supply Test connections and variable values, check dependency/import results, and verify flow state and sharing. Existing target values can suppress the variable prompt, so inspect the effective values explicitly. Import options can activate flows; unchecked activation does not stop already-active flows. [Import behavior](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/import-update-export-solutions)
6. **Prove isolation and security:** Confirm no non-Prod path writes Prod. Test app user, unauthorized user, segmented user, service flow, negative authorization, expected volumes, failed connections, and reauthentication. Capture business acceptance and technical evidence.
7. **Approve:** Named business and release owners approve the exact managed artifact and SharePoint/configuration changes. Any package change returns to Test.
8. **Deploy Prod:** Use that same managed artifact, with Prod-specific external mappings. Apply planned schema changes, establish a recovery point, restrict triggering while necessary, verify ownership/sharing, and enable only intended flows. Perform a small production smoke test and monitor failures.
9. **Close:** Record actual version/checksum, schema/configuration revision, deployment operator/time, approval, evidence, known issues, and recovery decision. Plan migration to genuine source control when available.

## Recovery and urgent fixes

An older ZIP is not a complete rollback plan. Updates require a higher version, and upgrades can remove components absent from the new package. **Recommendation:** Repackage corrected or previously known-good source as a new version for a tested forward recovery; preserve compatible SharePoint schemas until the recovery window closes. Do not use solution uninstall as routine rollback. [Upgrade or update a solution](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/update-solutions)

Power Platform environment backups cover solution-contained apps/flows, and restore is an environment-level operation with target/type restrictions. **Inference:** In shared environments, restoring to recover one solution can affect other solutions; it also does not constitute a coordinated rollback of external SharePoint content and permissions. Maintain separate SharePoint recovery procedures and rehearse the combined process. [Environment backup and restore](https://learn.microsoft.com/en-us/power-platform/admin/backup-restore-environments)

**Recommendation for only three environments:** Keep Dev release-ready using small changes and component edit coordination. If new feature work is already in progress when a production hotfix is required, explicitly freeze and reconcile it against the preserved release source; do not overwrite shared Dev casually. The absence of an isolated maintenance environment and source branching is a real limitation of this initial model.

## Remaining decisions

1. Are all apps standalone canvas apps, or are any SharePoint-customized forms involved? Are selected-item/file menu flows required?
2. Which operations should execute as the person using the app, and which deliberately execute as a service user? What server-side authorization protects the latter?
3. How many service identities exist, and which security domains must they isolate? Can Prod and non-Prod be separated at minimum?
4. Are these communication sites, Microsoft 365 group-connected sites, or another site pattern? Which inherited permissions and sharing mechanisms already exist?
5. Who can provision consistent lists, perform release imports, assign access, reauthenticate service connections, and approve emergency recovery?
6. What are the recovery objectives, expected volumes, allowable downtime, retention needs, and plan/date for adopting proper source control?

**Validation still required:** Run one complete Dev → Test → Prod pilot with a representative app and flow, actual SharePoint field types, least-privileged users, and a rehearsed recovery. This research validates the architecture's direction; it does not certify the customer's tenant implementation.
