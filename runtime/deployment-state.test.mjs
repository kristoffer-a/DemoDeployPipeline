import assert from "node:assert/strict";
import test from "node:test";
import {
  acceptDeploymentRequest,
  importPollOutcome,
  mayStartWorker,
  recordArchivedPackage,
  transitionRun,
} from "./deployment-state.mjs";

const configuration = {
  id: 1,
  solutionName: "Demo",
  sourceUrl: "https://devorgf20ef6ea.crm17.dynamics.com",
  targetUrl: "https://testorg5fd244de.crm17.dynamics.com",
};

test("accepts only the configured Demo DEV-to-TEST route", () => {
  assert.equal(acceptDeploymentRequest({ requestId: "request-1", configuration }).accepted, true);
  assert.deepEqual(
    acceptDeploymentRequest({ requestId: "request-2", configuration: { ...configuration, targetUrl: "https://example.invalid" } }),
    { accepted: false, error: "Configured route is not the approved DEV-to-TEST route." },
  );
});

test("reuses the existing run for a duplicate request ID", () => {
  const existingRun = { runId: "run-1", requestId: "request-1", state: "Running" };
  const result = acceptDeploymentRequest({ requestId: "request-1", configuration, existingRun });
  assert.equal(result.created, false);
  assert.equal(result.run, existingRun);
});

test("serializes the worker and rejects invalid state transitions", () => {
  const queued = acceptDeploymentRequest({ requestId: "request-1", configuration }).run;
  assert.equal(mayStartWorker({ activeRun: null, candidateRun: queued }), true);
  assert.equal(mayStartWorker({ activeRun: { state: "Running" }, candidateRun: queued }), false);
  assert.throws(() => transitionRun({ state: "NeedsAttention" }, "Running", "Retrying"), /Invalid deployment transition/);
});

test("retains exact package identity and does not resubmit an uncertain import", () => {
  assert.deepEqual(
    recordArchivedPackage({ fileUniqueId: "file-guid", versionId: "512.0", sha256: "abc" }),
    { fileUniqueId: "file-guid", versionId: "512.0", sha256: "abc" },
  );
  assert.throws(() => recordArchivedPackage({ fileUniqueId: "file-guid", versionId: "", sha256: "abc" }), /package requires/);
  assert.deepEqual(
    importPollOutcome({ state: "Running" }, { completed: false, jobId: "import-job-1" }),
    { state: "NeedsAttention", stage: "Import polling timed out", importJobId: "import-job-1" },
  );
});
