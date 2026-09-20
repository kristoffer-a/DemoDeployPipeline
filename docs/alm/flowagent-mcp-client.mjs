#!/usr/bin/env node

import { spawn } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import {
  assertApprovedLocalAuth,
  assertApprovedToolCall,
  buildIsolatedProcessEnvironment,
  redactSensitiveText,
} from "./flowagent-auth-policy.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(here, "..", "..");
const pluginRoot = path.join(
  projectRoot,
  ".tooling",
  "power-platform-skills-a804d33267c973314e21f56827e0743ee3f1e690",
  "plugins",
  "power-automate",
);
const serverPath = path.join(pluginRoot, "server", "mcp.mjs");

const cliArgs = process.argv.slice(2);
const allowMutatingIndex = cliArgs.indexOf("--allow-mutating");
const allowMutating = allowMutatingIndex >= 0;
if (allowMutating) cliArgs.splice(allowMutatingIndex, 1);
if (cliArgs.includes("--bootstrap-msal")) {
  throw new Error("--bootstrap-msal was retired after the approved bosso MSAL cache was established.");
}
const timeoutIndex = cliArgs.indexOf("--timeout-seconds");
let toolTimeoutSeconds = 120;
if (timeoutIndex >= 0) {
  toolTimeoutSeconds = Number(cliArgs[timeoutIndex + 1]);
  if (!Number.isInteger(toolTimeoutSeconds) || toolTimeoutSeconds < 1 || toolTimeoutSeconds > 900) {
    throw new Error("--timeout-seconds must be an integer from 1 through 900.");
  }
  cliArgs.splice(timeoutIndex, 2);
}
const outIndex = cliArgs.indexOf("--out");
let outputPath;
if (outIndex >= 0) {
  outputPath = cliArgs[outIndex + 1];
  if (!outputPath) throw new Error("--out requires a file path.");
  cliArgs.splice(outIndex, 2);
}
const [command = "list-tools", toolName, rawArguments = "{}"] = cliArgs;
if (!new Set(["list-tools", "call"]).has(command)) {
  throw new Error("Usage: node docs/alm/flowagent-mcp-client.mjs list-tools | call <tool-name> '<json-arguments-or-@file>' [--allow-mutating] [--timeout-seconds 120]");
}
if (command === "call" && !toolName) {
  throw new Error("The call command requires a tool name.");
}

let toolArguments = {};
if (command === "call") {
  const argumentText = rawArguments.startsWith("@")
    ? readFileSync(path.resolve(projectRoot, rawArguments.slice(1)), "utf8")
    : rawArguments;
  toolArguments = JSON.parse(argumentText);
}

if (command === "call") assertApprovedToolCall(toolName, toolArguments);

const localOnlyTools = new Set(["get_expression_help", "validate_flow"]);
if (command === "call" && !localOnlyTools.has(toolName)) {
  assertApprovedLocalAuth({ requireAzure: true, requireMsal: true });
}

const child = spawn(process.execPath, [serverPath], {
  cwd: pluginRoot,
  env: {
    ...buildIsolatedProcessEnvironment(),
    PATH: [
      "C:\\Program Files\\Microsoft SDKs\\Azure\\CLI2\\wbin",
      process.env.PATH ?? "",
    ].join(path.delimiter),
  },
  stdio: ["pipe", "pipe", "pipe"],
  windowsHide: true,
});

const protocolVersion = "2025-11-25";
let stdoutBuffer = "";
let stderrBuffer = "";
let initializeResult;
let nextRequestId = 2;
const tools = [];
let finished = false;
let awaitingToolCall = false;

let timeout = setTimeout(() => finishWithError("Timed out during FlowAgent startup or tool discovery; no tool was dispatched."), 20_000);

child.stderr.setEncoding("utf8");
child.stderr.on("data", (chunk) => {
  stderrBuffer += chunk;
});

child.stdout.setEncoding("utf8");
child.stdout.on("data", (chunk) => {
  stdoutBuffer += chunk;
  while (stdoutBuffer.includes("\n")) {
    const newline = stdoutBuffer.indexOf("\n");
    const line = stdoutBuffer.slice(0, newline).replace(/\r$/, "");
    stdoutBuffer = stdoutBuffer.slice(newline + 1);
    if (!line.trim()) continue;
    handleMessage(JSON.parse(line));
  }
});

child.once("error", (error) => finishWithError(`Could not start FlowAgent: ${error.message}`));
child.once("exit", (code) => {
  if (!finished && code !== 0) {
    finishWithError(`FlowAgent exited with code ${code}.`);
  }
});

send({
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    protocolVersion,
    capabilities: {},
    clientInfo: { name: "adminenv-flowagent-client", version: "1.0.0" },
  },
});

function send(message) {
  child.stdin.write(`${JSON.stringify(message)}\n`);
}

function handleMessage(message) {
  if (message.id === 1) {
    if (message.error) return finishWithError(`Initialize failed: ${JSON.stringify(message.error)}`);
    initializeResult = message.result;
    send({ jsonrpc: "2.0", method: "notifications/initialized", params: {} });
    return requestTools();
  }

  if (message.id !== nextRequestId) return;
  if (message.error) return finishWithError(`MCP request failed: ${JSON.stringify(message.error)}`);

  if (awaitingToolCall) {
    return finish({
      server: initializeResult?.serverInfo,
      protocolVersion: initializeResult?.protocolVersion,
      tool: toolName,
      result: message.result,
    });
  }

  tools.push(...(message.result?.tools ?? []));
  if (message.result?.nextCursor) {
    nextRequestId += 1;
    return requestTools(message.result.nextCursor);
  }

  if (command === "call") {
    const selectedTool = tools.find((tool) => tool.name === toolName);
    if (!selectedTool) return finishWithError(`FlowAgent does not advertise a tool named '${toolName}'.`);
    if (selectedTool.annotations?.readOnlyHint !== true && !allowMutating) {
      return finishWithError(
        `Refusing '${toolName}' because it is not explicitly read-only. Re-run with --allow-mutating only after reviewing the target and arguments.`,
      );
    }
    awaitingToolCall = true;
    nextRequestId += 1;
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      const outcome = selectedTool.annotations?.readOnlyHint === true
        ? "The read-only call did not complete."
        : "Outcome unknown: the tool may have committed a tenant change. Do not retry until live state has been read back.";
      finishWithError(`FlowAgent tool '${toolName}' timed out after ${toolTimeoutSeconds}s. ${outcome}`);
    }, toolTimeoutSeconds * 1000);
    send({
      jsonrpc: "2.0",
      id: nextRequestId,
      method: "tools/call",
      params: { name: toolName, arguments: toolArguments },
    });
    return;
  }

  finish({
    sourceRevision: "a804d33267c973314e21f56827e0743ee3f1e690",
    server: initializeResult?.serverInfo,
    protocolVersion: initializeResult?.protocolVersion,
    toolCount: tools.length,
    tools,
  });
}

function requestTools(cursor) {
  send({
    jsonrpc: "2.0",
    id: nextRequestId,
    method: "tools/list",
    params: cursor ? { cursor } : {},
  });
}

function finish(value) {
  if (finished) return;
  finished = true;
  clearTimeout(timeout);
  const json = redactSensitiveText(`${JSON.stringify(value, null, 2)}\n`);
  if (outputPath) {
    const resolvedOutput = path.isAbsolute(outputPath)
      ? outputPath
      : path.resolve(projectRoot, outputPath);
    writeFileSync(resolvedOutput, json, "utf8");
    process.stdout.write(`${JSON.stringify({ written: resolvedOutput, toolCount: value.toolCount })}\n`);
  } else {
    process.stdout.write(json);
  }
  child.kill();
}

function finishWithError(message) {
  if (finished) return;
  finished = true;
  clearTimeout(timeout);
  process.exitCode = 1;
  const details = redactSensitiveText(stderrBuffer.trim());
  process.stderr.write(`${redactSensitiveText(message)}${details ? `\n${details}` : ""}\n`);
  child.kill();
}
