import assert from "node:assert/strict";
import test from "node:test";
import {
  approvedIdentity,
  assertApprovedEnvironmentArguments,
  assertApprovedToolCall,
  buildIsolatedProcessEnvironment,
  redactSensitiveText,
} from "./flowagent-auth-policy.mjs";

test("isolated environment pins endpoints, tenant, client, and cache locations", () => {
  const environment = buildIsolatedProcessEnvironment({
    PA_BASE_URL: "https://attacker.invalid",
    PA_PPAPI_BASE_URL: "https://attacker.invalid",
    PA_PPAPI_SUFFIX: "attacker.invalid",
    PA_CLIENT_ID: "attacker-client",
    PA_CLOUD: "attacker-cloud",
  });
  assert.equal(environment.PA_TENANT_ID, approvedIdentity.tenantId);
  assert.equal(environment.PA_BASE_URL, "https://api.flow.microsoft.com");
  assert.equal(environment.PA_PPAPI_SUFFIX, "environment.api.powerplatform.com");
  assert.equal(environment.PA_CLIENT_ID, "9cee029c-6210-4654-90bb-17e6e9d36617");
  assert.equal(environment.PA_CLOUD, "commercial");
  assert.equal("PA_PPAPI_BASE_URL" in environment, false);
});

test("environment argument policy allows only the three approved tenant environments", () => {
  for (const environmentId of approvedIdentity.environmentIds) {
    assert.doesNotThrow(() => assertApprovedEnvironmentArguments({ env: environmentId }));
  }
  assert.throws(
    () => assertApprovedEnvironmentArguments({ targetEnv: "00000000-0000-0000-0000-000000000000" }),
    /TENANT TARGET BLOCKED/,
  );
});

test("tool-call policy blocks auth changes and unapproved targets without reading caches", () => {
  assert.throws(() => assertApprovedToolCall("reconnect", {}), /AUTH BLOCKED/);
  assert.throws(
    () => assertApprovedToolCall("list_flows", { env: "00000000-0000-0000-0000-000000000000" }),
    /TENANT TARGET BLOCKED/,
  );
});

test("redaction covers bearer, structured tokens, cookies, SAS signatures, and URL queries", () => {
  const source = 'Bearer abc.def {"accessToken":"VALUE_A","access_token":"VALUE_B","refresh_token":"VALUE_C","client_secret":"VALUE_D","id_token":"VALUE_E","cookie":"VALUE_F"} https://example.test/x?sig=VALUE_G&code=VALUE_H';
  const redacted = redactSensitiveText(source);
  assert.doesNotMatch(redacted, /abc\.def|VALUE_[A-H]/);
  assert.match(redacted, /\[REDACTED\]/);
});
