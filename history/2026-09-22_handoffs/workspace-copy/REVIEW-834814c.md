# Review of 834814c — 2026-09-22

Base: `8335c7661b032fbd81679bcdeef693e2f6139be6`.
Reviewed head: `834814c3c658f3c1b692ce36cfb72d9b701527bc`.
One commit: Add deployment state checks and test runbook.

Scope: static two-axis review and isolated local checks only. The task's user-provided implementation handoff and existing ALM spec are the requirements; there is no issue-tracker configuration or repository coding-standards document in this snapshot. No issue-tracker setup is needed for this review.

The author reported a locally installed pinned bundle and a 59-tool discovery. Those are machine-local observations, not committed deliverables and not independently repeated in this review.

## Validation

Independently ran from an isolated snapshot with Node 22.23.2:

```sh
node --test docs/alm/flowagent-auth-policy.test.mjs runtime/deployment-state.test.mjs
```

Result: 8 passed, 0 failed. These tests do not establish deployed flow behavior, concurrent persistence, successful tenant authentication or export/import integration.

Additional pure-function reproductions:
- Approved route + a new RequestId + an existing run with a different RequestId/configuration returns the unrelated run as accepted.
- A successful poll applied to a terminal run overwrites its job/stage.
- Two candidates evaluating the same idle snapshot both pass `mayStartWorker`.
- `XDG_STATE_HOME=relative-review-state` makes the exported Azure cache path relative. Only module initialization and path checks ran; no cache was read or written.
- `completed:false` immediately yields NeedsAttention; the helper has no separate pending/deadline signal. Either call it only after a polling loop finishes and document that contract, or model pending vs timeout explicitly.

No tenant API/helper calls, browser interaction, login, authentication-cache inspection, import or permission changes were performed.

## Standards

Three correctness findings, all addressable locally before authentication:

1. **P2 — Duplicate-request safeguard does not verify identity** (`runtime/deployment-state.mjs:28`). Passing a new request with an existing run for another RequestId/configuration returns that unrelated run as accepted. Check matching RequestId and configuration before reusing a run; reject conflicting reuse. Actual concurrent deduplication additionally requires an atomic persistence constraint.

2. **P2 — Successful polling bypasses state/job guards** (`runtime/deployment-state.mjs:68`). A successful result can change a terminal run's job ID and stage to Verifying target while leaving its terminal state intact. Validate the eligible state and matching stored job ID before every polling branch. Define deliberate reconciliation of NeedsAttention separately from deployment retry.

3. **P2 — Cache location guarantee is not enforced** (`docs/alm/flowagent-auth-policy.mjs:16–19`). Empty/relative LOCALAPPDATA or XDG_STATE_HOME, or a configured directory inside the checkout, can yield cache paths inside the repository. README requires caches outside it. Validate a usable absolute external root and test invalid/in-repository roots hermetically. The current test only checks the host's inherited configuration. Do not move, inspect or delete existing caches while addressing this.

No additional style findings warrant changes; the helpers are readable.

## Spec

Partial implementation; four findings. No scope creep.

1. **Duplicate requests are not correlated.** The spec says “Reuse a matching RequestId”; `acceptDeploymentRequest` accepts any supplied existingRun. Validate request/configuration identity; persistence must enforce request uniqueness atomically.

2. **Successful polling bypasses state protection.** The spec requires actual import status and preservation of job IDs. Success bypasses the guards used by timeout/failure branches. Require an eligible Running import and matching job identity; explicitly design later reconciliation of NeedsAttention.

3. **Runtime remains missing.** The spec requires request/worker flows that write a run JSON file, return RunId promptly and execute one deployment at a time. The additions create an in-memory object without RunId and check an activeRun snapshot. There is no persistent queue, atomic claim, trigger exclusion, connector integration, package storage or target verification. Tests exercise supplied objects rather than concurrency or persistent retry behavior. Describe these additions as a local behavioral model, not implemented Power Automate safeguards.

4. **Runbook must explicitly import the archived managed bytes.** The user handoff requires deploying the managed package retained in SharePoint. `docs/alm/test-runbook.md:16–18` exports/archives, then refers to export/download/import again. Move export polling into the export step; retrieve the recorded managed file/version, verify its hash and use those exact bytes for import. Do not accidentally re-export after archiving.

The runbook otherwise covers first/repeat deployment, distinct Test data, configuration failures and uncertain import outcomes. It is test preparation, not evidence of execution.

Summary: Standards — 3 findings, with unvalidated retry identity and state/job mutation most consequential within that axis. Spec — 4 findings, with missing deployed request/worker implementation the largest coverage gap.

## Disposition

This review publishes findings and continuation instructions only; no implementation fixes are claimed. The existing commit is useful local groundwork but is not approved as a deployment-ready pipeline. Resolve the local findings, implement the actual Power Platform components, and collect tenant evidence before claiming readiness.

See [current remote handoff](HANDOFF-REMOTE-2026-09-22.md).

