const demoRoute = Object.freeze({
  solutionName: "Demo",
  sourceUrl: "https://devorgf20ef6ea.crm17.dynamics.com",
  targetUrl: "https://testorg5fd244de.crm17.dynamics.com",
});

const terminalStates = new Set(["Succeeded", "Failed", "NeedsAttention"]);
const allowedTransitions = Object.freeze({
  Queued: new Set(["Running", "Failed"]),
  Running: new Set(["Succeeded", "Failed", "NeedsAttention"]),
});

export function validateDeploymentRequest({ requestId, configuration }) {
  if (typeof requestId !== "string" || !requestId.trim()) return "RequestId is required.";
  if (!configuration || !Number.isInteger(configuration.id) || configuration.id < 1) {
    return "Configured route ID is required.";
  }
  if (configuration.solutionName !== demoRoute.solutionName) return "Only the Demo route is allowed.";
  if (configuration.sourceUrl !== demoRoute.sourceUrl || configuration.targetUrl !== demoRoute.targetUrl) {
    return "Configured route is not the approved DEV-to-TEST route.";
  }
  return null;
}

export function acceptDeploymentRequest({ requestId, configuration, existingRun }) {
  const error = validateDeploymentRequest({ requestId, configuration });
  if (error) return { accepted: false, error };
  if (existingRun) return { accepted: true, created: false, run: existingRun };
  return {
    accepted: true,
    created: true,
    run: {
      requestId,
      configurationId: configuration.id,
      solutionName: configuration.solutionName,
      state: "Queued",
      stage: "Queued",
    },
  };
}

export function mayStartWorker({ activeRun, candidateRun }) {
  return candidateRun?.state === "Queued" && !activeRun;
}

export function transitionRun(run, state, stage, details = {}) {
  if (!run || terminalStates.has(run.state) || !allowedTransitions[run.state]?.has(state)) {
    throw new Error(`Invalid deployment transition: ${run?.state ?? "missing"} -> ${state}`);
  }
  return { ...run, ...details, state, stage };
}

export function recordArchivedPackage({ fileUniqueId, versionId, sha256 }) {
  if (![fileUniqueId, versionId, sha256].every((value) => typeof value === "string" && value.trim())) {
    throw new Error("Archived package requires SharePoint file identity, version identity, and SHA-256.");
  }
  return { fileUniqueId, versionId, sha256 };
}

export function importPollOutcome(run, { completed, succeeded, jobId, error }) {
  if (!jobId) throw new Error("Import job ID is required.");
  if (!completed) {
    return transitionRun(run, "NeedsAttention", "Import polling timed out", { importJobId: jobId });
  }
  if (!succeeded) {
    return transitionRun(run, "Failed", "Import failed", { importJobId: jobId, error });
  }
  return { ...run, importJobId: jobId, stage: "Verifying target" };
}
