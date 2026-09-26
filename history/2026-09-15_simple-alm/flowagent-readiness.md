# FlowAgent local readiness — 2026-09-17

## Result

The pinned FlowAgent bundle starts successfully as an MCP stdio server. A local
`initialize` + `notifications/initialized` + paginated `tools/list` exchange
negotiated MCP protocol `2025-11-25` with `flowagent-mcp` version `2.0.0` and
returned 59 unique tool schemas. Every tool has an `inputSchema`.

The captured response is [flowagent-tools.json](flowagent-tools.json):

- source revision: `a804d33267c973314e21f56827e0743ee3f1e690`
- size: 66,509 bytes
- SHA-256: `B2797B8DBFA1AB0041A9AFE1BA1A440713E5124F3884FDA7A48FD3FE5C6358C4`

This handshake did not call a FlowAgent tool, acquire a token, or contact a
Power Platform tenant. The successful startup and schema exchange indicate the
bundle itself is healthy. The tools being absent from the current Codex tool
surface is therefore a host/session loading issue; project MCP registrations
normally become available only to a newly loaded task after the configuration
exists.

## Supported local path

The shipped plugin contains `server/mcp.mjs`, a self-contained stdio MCP server.
Its `references/cli-reference.md` explicitly says the documented
`node dist/cli.js ...` commands require a separate local engine build;
`dist/cli.js` is not included in this pinned plugin. Do not use that CLI path.

Use the dependency-free diagnostic client instead:

```powershell
# Refresh the local schema capture (no tenant call)
node docs/alm/flowagent-mcp-client.mjs list-tools --out docs/alm/flowagent-tools.json

# Call an advertised read-only tool; arguments can be inline JSON
node docs/alm/flowagent-mcp-client.mjs call get_expression_help '{"query":"concat"}'

# Prefer a file for large or shell-sensitive arguments
node docs/alm/flowagent-mcp-client.mjs call validate_flow '@docs/alm/validate-flow-args.json'

# Mutating/unannotated tools require an explicit safety override
node docs/alm/flowagent-mcp-client.mjs call create_flow '@docs/alm/create-flow-args.json' --allow-mutating --timeout-seconds 180
```

The helper prepends the verified Azure CLI directory
`C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin` to the child process `PATH`.
It starts a fresh FlowAgent process for each command, performs the MCP handshake,
verifies that the requested tool is advertised, and refuses any tool lacking
`annotations.readOnlyHint: true` unless `--allow-mutating` is supplied. A local
safety test confirmed `create_flow` is rejected without that flag.

Startup and schema discovery have a fixed 20-second timeout. Once a tool is
dispatched, the timeout resets to 120 seconds by default and can be set from 1
through 900 seconds with `--timeout-seconds`. If a mutating or unannotated tool
times out, the helper reports the outcome as unknown. Do not retry it until live
state has been read back using a read-only operation.

## Limitations

- The helper is a fallback for the current task; a newly loaded Codex task with
  the project MCP configuration should use native `mcp__flowagent__*` tools.
- Each invocation has a fresh MCP session. Pass explicit environment and flow
  identifiers rather than relying on session-pinned state.
- Read-only tools can still make tenant network requests. Confirm target IDs and
  current Azure identity before any tenant call.
- `--allow-mutating` only removes the local guard. It does not replace required
  review, confirmation, preflight, or the `build-flow` workflow.
- A process timeout cannot prove that a remote write failed. Treat a timed-out
  mutation as potentially committed and verify live state before deciding what
  to do next.
- Keep credentials and access tokens out of argument files and captured output.
- Startup currently emits Node deprecation warning `DEP0190` from bundled code;
  it does not prevent initialization or schema discovery.

## Verification commands

```powershell
node --check docs/alm/flowagent-mcp-client.mjs
node docs/alm/flowagent-mcp-client.mjs list-tools --out docs/alm/flowagent-tools.json
node docs/alm/flowagent-mcp-client.mjs call create_flow '{}'
```

Observed exit codes were `0`, `0`, and `1` respectively; the last result is the
expected local mutation guard.
