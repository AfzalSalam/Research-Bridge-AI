import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = path.resolve(webRoot, "../..");
const nextCli = path.join(workspaceRoot, "node_modules", "next", "dist", "bin", "next");
const playwrightCli = path.join(
  workspaceRoot,
  "node_modules",
  "@playwright",
  "test",
  "cli.js",
);
const baseUrl = "http://127.0.0.1:3100";

function forwardOutput(stream, destination) {
  stream.on("data", (chunk) => destination.write(chunk));
}

async function waitForServer(server) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (server.exitCode !== null) {
      throw new Error(`Next.js exited before E2E startup with code ${server.exitCode}.`);
    }
    try {
      const response = await fetch(baseUrl);
      if (response.ok) return;
    } catch {
      // The production server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Timed out waiting for the Next.js E2E server.");
}

async function stopServer(server) {
  if (server.exitCode !== null) return;
  server.kill();
  await Promise.race([
    new Promise((resolve) => server.once("exit", resolve)),
    new Promise((resolve) => setTimeout(resolve, 2_000)),
  ]);
}

const server = spawn(
  process.execPath,
  [nextCli, "start", "--hostname", "127.0.0.1", "--port", "3100"],
  { cwd: webRoot, env: process.env, stdio: ["ignore", "pipe", "pipe"] },
);
forwardOutput(server.stdout, process.stdout);
forwardOutput(server.stderr, process.stderr);

let exitCode = 1;
try {
  await waitForServer(server);
  const tests = spawn(process.execPath, [playwrightCli, "test"], {
    cwd: webRoot,
    env: { ...process.env, PLAYWRIGHT_EXTERNAL_SERVER: "1" },
    stdio: "inherit",
  });
  exitCode = await new Promise((resolve) => tests.once("exit", (code) => resolve(code ?? 1)));
} finally {
  await stopServer(server);
}

process.exitCode = exitCode;
