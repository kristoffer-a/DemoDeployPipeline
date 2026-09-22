import { existsSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

export const approvedIdentity = Object.freeze({
  tenantId: "1c5afb69-a82c-4c81-b2cc-743ce7f91dac",
  username: "bosso@7xpydh.onmicrosoft.com",
  environmentId: "8f7d7c0e-e59d-e988-9dde-4ca7428aa659",
  environmentIds: Object.freeze([
    "8f7d7c0e-e59d-e988-9dde-4ca7428aa659",
    "8fcc484b-d74e-e479-84da-ad5a78d6d55b",
    "f2280ea5-6793-e664-8f21-ea3ba6a4cb5c",
  ]),
});

const localAppData = process.env.LOCALAPPDATA
  ?? process.env.XDG_STATE_HOME
  ?? path.join(homedir(), ".local", "state");
const authRoot = path.join(localAppData, "flowagent", "projects", "AdminEnv-7xpydh-bosso");

export const isolatedAuthEnvironment = Object.freeze({
  PA_TENANT_ID: approvedIdentity.tenantId,
  PA_DEFAULT_ENVIRONMENT: approvedIdentity.environmentId,
  PA_CLOUD: "commercial",
  PA_BASE_URL: "https://api.flow.microsoft.com",
  PA_PPAPI_SUFFIX: "environment.api.powerplatform.com",
  PA_CLIENT_ID: "9cee029c-6210-4654-90bb-17e6e9d36617",
  FLOWAGENT_TENANT_ID: approvedIdentity.tenantId,
  AZURE_CONFIG_DIR: path.join(authRoot, "azure"),
  FLOWAGENT_TOKEN_CACHE_DIR: path.join(authRoot, "tokens"),
  FLOWAGENT_MSAL_CACHE_DIR: path.join(authRoot, "msal-cache"),
});

const removedEnvironmentKeys = Object.freeze([
  "PA_PPAPI_BASE_URL",
]);

export function buildIsolatedProcessEnvironment(baseEnvironment = process.env) {
  const environment = { ...baseEnvironment, ...isolatedAuthEnvironment };
  for (const key of removedEnvironmentKeys) delete environment[key];
  return environment;
}

export function assertApprovedEnvironmentArguments(value) {
  const allowed = new Set(approvedIdentity.environmentIds.map((item) => item.toLowerCase()));
  const visit = (current, key = "") => {
    if (Array.isArray(current)) {
      current.forEach((item) => visit(item, key));
      return;
    }
    if (!current || typeof current !== "object") return;
    for (const [childKey, childValue] of Object.entries(current)) {
      if (/^(env|environment|environmentid|sourceenv|targetenv)$/i.test(childKey)
        && typeof childValue === "string"
        && !allowed.has(childValue.toLowerCase())) {
        throw new Error(`TENANT TARGET BLOCKED: ${childKey} '${childValue}' is not an approved 7xpydh environment.`);
      }
      visit(childValue, childKey);
    }
  };
  visit(value);
}

export function assertApprovedToolCall(toolName, toolArguments = {}) {
  if (toolName === "reconnect") {
    throw new Error("AUTH BLOCKED: tool 'reconnect' can change authentication state.");
  }
  assertApprovedEnvironmentArguments(toolArguments);
}

export function redactSensitiveText(value) {
  return String(value)
    .replace(/(Bearer\s+)[A-Za-z0-9._~+\/-]+/gi, "$1[REDACTED]")
    .replace(/((?:access_token|refresh_token|client_secret|authorization_code|code|sig)=)[^&\s]+/gi, "$1[REDACTED]")
    .replace(/("(?:accessToken|access_token|refreshToken|refresh_token|clientSecret|client_secret|idToken|id_token|authorization|cookie|set-cookie)"\s*:\s*")[^"]+/gi, "$1[REDACTED]")
    .replace(/(https:\/\/[^\s?]+)\?[^\s"]+/gi, "$1?[REDACTED]");
}

function same(left, right) {
  return typeof left === "string" && left.toLowerCase() === right.toLowerCase();
}

function readJson(file) {
  return JSON.parse(readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
}

export function inspectLocalAuth() {
  const profilePath = path.join(isolatedAuthEnvironment.AZURE_CONFIG_DIR, "azureProfile.json");
  let azure = { status: "missing", profilePath };
  if (existsSync(profilePath)) {
    const profile = readJson(profilePath);
    const subscriptions = Array.isArray(profile?.subscriptions) ? profile.subscriptions : [];
    const active = subscriptions.find((item) => item?.isDefault) ?? subscriptions[0];
    azure = active
      ? { status: "present", tenantId: active.tenantId, username: active.user?.name, profilePath }
      : { status: "empty", profilePath };
  }

  const accounts = [];
  const cacheDir = isolatedAuthEnvironment.FLOWAGENT_MSAL_CACHE_DIR;
  if (existsSync(cacheDir)) {
    for (const name of readdirSync(cacheDir).filter((item) => item.endsWith(".json"))) {
      const cache = readJson(path.join(cacheDir, name));
      for (const property of Object.values(cache?.Account ?? {})) {
        accounts.push({ tenantId: property?.realm, username: property?.username, file: name });
      }
    }
  }

  return { azure, msal: { status: accounts.length ? "present" : "missing", accounts, cacheDir } };
}

export function assertApprovedLocalAuth({ requireAzure = true, requireMsal = true } = {}) {
  const state = inspectLocalAuth();
  if (requireAzure) {
    const approved = state.azure.status === "present"
      && same(state.azure.tenantId, approvedIdentity.tenantId)
      && same(state.azure.username, approvedIdentity.username);
    if (!approved) {
      throw new Error(
        `AUTH BLOCKED: isolated Azure profile is not ${approvedIdentity.username} in tenant ${approvedIdentity.tenantId}. `
        + `Observed ${state.azure.username ?? "no account"} in ${state.azure.tenantId ?? "no tenant"}.`,
      );
    }
  }

  if (requireMsal) {
    const approved = state.msal.accounts.length > 0
      && state.msal.accounts.every((account) => same(account.tenantId, approvedIdentity.tenantId)
        && same(account.username, approvedIdentity.username));
    if (!approved) {
      const observed = state.msal.accounts.length
        ? state.msal.accounts.map((account) => `${account.username ?? "unknown"}@${account.tenantId ?? "unknown"}`).join(", ")
        : "no account";
      throw new Error(
        `AUTH BLOCKED: isolated FlowAgent MSAL cache is not exclusively ${approvedIdentity.username} `
        + `in tenant ${approvedIdentity.tenantId}. Observed ${observed}.`,
      );
    }
  }
  return state;
}
