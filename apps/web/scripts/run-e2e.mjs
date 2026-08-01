import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = path.resolve(webRoot, "../..");
const apiRoot = path.join(workspaceRoot, "apps", "api");
const nextCli = path.join(workspaceRoot, "node_modules", "next", "dist", "bin", "next");
const playwrightCli = path.join(
  workspaceRoot,
  "node_modules",
  "@playwright",
  "test",
  "cli.js",
);
const pythonExecutable =
  process.platform === "win32"
    ? path.join(apiRoot, ".venv", "Scripts", "python.exe")
    : path.join(apiRoot, ".venv", "bin", "python");
const webBaseUrl = "http://127.0.0.1:3100";
const apiBaseUrl = "http://127.0.0.1:8100";
const apiHealthUrl = `${apiBaseUrl}/api/v1/health`;

function forwardOutput(stream, destination) {
  stream.on("data", (chunk) => destination.write(chunk));
}

async function runCommand(command, args, options) {
  const child = spawn(command, args, { ...options, stdio: "inherit" });
  const exitCode = await new Promise((resolve) =>
    child.once("exit", (code) => resolve(code ?? 1)),
  );
  if (exitCode !== 0) {
    throw new Error(`${path.basename(command)} exited with code ${exitCode}.`);
  }
}

async function waitForUrl({ process: child, url, label, validate }) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (child?.exitCode !== null && child?.exitCode !== undefined) {
      throw new Error(`${label} exited before startup with code ${child.exitCode}.`);
    }
    try {
      const response = await fetch(url);
      if (response.ok && (!validate || (await validate(response)))) return;
    } catch {
      // The owned server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for ${label}.`);
}

async function stopServer(server) {
  if (!server || server.exitCode !== null) return;
  const exitPromise = new Promise((resolve) =>
    server.once("exit", () => resolve(true)),
  );
  server.kill();
  const exited = await Promise.race([
    exitPromise,
    new Promise((resolve) => setTimeout(() => resolve(false), 2_000)),
  ]);
  if (!exited) {
    server.kill("SIGKILL");
    const forceExited = await Promise.race([
      exitPromise,
      new Promise((resolve) => setTimeout(() => resolve(false), 5_000)),
    ]);
    if (!forceExited) {
      throw new Error(`Server process ${server.pid} did not stop during cleanup.`);
    }
  }
  server.stdout?.destroy();
  server.stderr?.destroy();
}

if (!existsSync(pythonExecutable)) {
  throw new Error(
    `Backend environment not found at ${pythonExecutable}. Run "uv sync --all-groups" in apps/api first.`,
  );
}

const temporaryRoot = await mkdtemp(path.join(tmpdir(), "research-bridge-e2e-"));
const databasePath = path.join(temporaryRoot, "e2e.sqlite3").replaceAll("\\", "/");
const databaseUrl = `sqlite+aiosqlite:///${databasePath}`;
const apiEnvironment = {
  ...process.env,
  APP_ENVIRONMENT: "e2e",
  DATABASE_URL: databaseUrl,
  LOG_LEVEL: "WARNING",
};
const webEnvironment = { ...process.env, API_BASE_URL: apiBaseUrl };

let apiServer = null;
let webServer = null;
let exitCode = 1;
try {
  await runCommand(pythonExecutable, ["-m", "alembic", "upgrade", "head"], {
    cwd: apiRoot,
    env: apiEnvironment,
  });
  await runCommand(process.execPath, [nextCli, "build"], {
    cwd: webRoot,
    env: webEnvironment,
  });

  apiServer = spawn(
    pythonExecutable,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8100"],
    {
      cwd: apiRoot,
      env: apiEnvironment,
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  forwardOutput(apiServer.stdout, process.stdout);
  forwardOutput(apiServer.stderr, process.stderr);
  await waitForUrl({
    process: apiServer,
    url: apiHealthUrl,
    label: "isolated FastAPI E2E server",
    validate: async (response) => (await response.json()).status === "ok",
  });

  webServer = spawn(
    process.execPath,
    [nextCli, "start", "--hostname", "127.0.0.1", "--port", "3100"],
    { cwd: webRoot, env: webEnvironment, stdio: ["ignore", "pipe", "pipe"] },
  );
  forwardOutput(webServer.stdout, process.stdout);
  forwardOutput(webServer.stderr, process.stderr);
  await waitForUrl({
    process: webServer,
    url: webBaseUrl,
    label: "Next.js E2E server",
  });

  const tests = spawn(process.execPath, [playwrightCli, "test"], {
    cwd: webRoot,
    env: { ...process.env, PLAYWRIGHT_EXTERNAL_SERVER: "1" },
    stdio: "inherit",
  });
  exitCode = await new Promise((resolve) =>
    tests.once("exit", (code) => resolve(code ?? 1)),
  );
} finally {
  const shutdownResults = await Promise.allSettled([
    stopServer(webServer),
    stopServer(apiServer),
  ]);
  await rm(temporaryRoot, {
    force: true,
    maxRetries: 5,
    recursive: true,
    retryDelay: 200,
  });
  const shutdownFailure = shutdownResults.find(
    (result) => result.status === "rejected",
  );
  if (shutdownFailure?.status === "rejected") throw shutdownFailure.reason;
}

process.exit(exitCode);
