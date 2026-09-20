#!/usr/bin/env node

import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import {
  assertApprovedLocalAuth,
  assertApprovedToolCall,
  buildIsolatedProcessEnvironment,
  redactSensitiveText,
} from "./flowagent-auth-policy.mjs";

assertApprovedLocalAuth({ requireAzure: true, requireMsal: true });

const here = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(here, "..", "..");
const serverPath = path.join(
  projectRoot,
  ".tooling",
  "power-platform-skills-a804d33267c973314e21f56827e0743ee3f1e690",
  "plugins",
  "power-automate",
  "server",
  "mcp.mjs",
);

const child = spawn(process.execPath, [serverPath], {
  cwd: path.dirname(serverPath),
  env: {
    ...buildIsolatedProcessEnvironment(),
    PATH: ["C:\\Program Files\\Microsoft SDKs\\Azure\\CLI2\\wbin", process.env.PATH ?? ""].join(path.delimiter),
  },
  stdio: ["pipe", "pipe", "pipe"],
  windowsHide: true,
});

const localOnlyTools = new Set(["get_expression_help", "validate_flow", "list_templates"]);
let stdinBuffer = "";
let stdoutBuffer = "";
let stderrBuffer = "";

process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  stdinBuffer += chunk;
  while (stdinBuffer.includes("\n")) {
    const newline = stdinBuffer.indexOf("\n");
    const line = stdinBuffer.slice(0, newline).replace(/\r$/, "");
    stdinBuffer = stdinBuffer.slice(newline + 1);
    if (!line.trim()) continue;
    forwardApprovedRequest(line);
  }
});
process.stdin.on("end", () => child.stdin.end());

child.stdout.setEncoding("utf8");
child.stdout.on("data", (chunk) => {
  stdoutBuffer += chunk;
  stdoutBuffer = flushCompleteLines(stdoutBuffer, process.stdout);
});
child.stdout.on("end", () => {
  if (stdoutBuffer) process.stdout.write(redactSensitiveText(stdoutBuffer));
  stdoutBuffer = "";
});
child.stderr.setEncoding("utf8");
child.stderr.on("data", (chunk) => {
  stderrBuffer += chunk;
  stderrBuffer = flushCompleteLines(stderrBuffer, process.stderr);
});
child.stderr.on("end", () => {
  if (stderrBuffer) process.stderr.write(redactSensitiveText(stderrBuffer));
  stderrBuffer = "";
});

child.once("error", (error) => {
  process.stderr.write(`AUTH-GUARDED FlowAgent could not start: ${redactSensitiveText(error.message)}\n`);
  process.exitCode = 1;
});
child.once("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  else process.exitCode = code ?? 1;
});

function forwardApprovedRequest(line) {
  let message;
  try {
    message = JSON.parse(line);
  } catch {
    process.stderr.write("AUTH-GUARDED FlowAgent blocked malformed JSON-RPC input.\n");
    return;
  }

  try {
    if (message?.method === "tools/call") {
      const toolName = message?.params?.name;
      const toolArguments = message?.params?.arguments ?? {};
      assertApprovedToolCall(toolName, toolArguments);
      if (!localOnlyTools.has(toolName)) {
        assertApprovedLocalAuth({ requireAzure: true, requireMsal: true });
      }
    }
    child.stdin.write(`${line}\n`);
  } catch (error) {
    const messageText = redactSensitiveText(error instanceof Error ? error.message : String(error));
    if (message?.id !== undefined) {
      process.stdout.write(`${JSON.stringify({
        jsonrpc: "2.0",
        id: message.id,
        error: { code: -32001, message: messageText },
      })}\n`);
    }
    process.stderr.write(`${messageText}\n`);
  }
}

function flushCompleteLines(buffer, destination) {
  let remaining = buffer;
  while (remaining.includes("\n")) {
    const newline = remaining.indexOf("\n");
    const line = remaining.slice(0, newline + 1);
    remaining = remaining.slice(newline + 1);
    destination.write(redactSensitiveText(line));
  }
  return remaining;
}
