import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

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
const webBaseUrl = "http://127.0.0.1:3100";
const apiHealthUrl = "http://127.0.0.1:8000/api/v1/health";

function forwardOutput(stream, destination) {
  stream.on("data", (chunk) => destination.write(chunk));
}

async function isHealthyApi() {
  try {
    const response = await fetch(apiHealthUrl);
    if (!response.ok) return false;
    const payload = await response.json();
    return payload.status === "ok" && payload.service === "research-bridge-api";
  } catch {
    return false;
  }
}

async function waitForUrl({ process, url, label, validate }) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (process?.exitCode !== null && process?.exitCode !== undefined) {
      throw new Error(`${label} exited before startup with code ${process.exitCode}.`);
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
  server.kill();
  const exited = await Promise.race([
    new Promise((resolve) => server.once("exit", () => resolve(true))),
    new Promise((resolve) => setTimeout(() => resolve(false), 2_000)),
  ]);
  if (!exited) {
    server.kill("SIGKILL");
  }
  server.stdout?.destroy();
  server.stderr?.destroy();
}

let apiServer = null;
let webServer = null;
let exitCode = 1;
try {
  if (!(await isHealthyApi())) {
    const pythonExecutable =
      process.platform === "win32"
        ? path.join(apiRoot, ".venv", "Scripts", "python.exe")
        : path.join(apiRoot, ".venv", "bin", "python");
    if (!existsSync(pythonExecutable)) {
      throw new Error(
        `Backend environment not found at ${pythonExecutable}. Run "uv sync --all-groups" in apps/api first.`,
      );
    }
    apiServer = spawn(
      pythonExecutable,
      [
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
      ],
      {
        cwd: apiRoot,
        env: {
          ...process.env,
          APP_ENVIRONMENT: "e2e",
          LOG_LEVEL: "WARNING",
        },
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    forwardOutput(apiServer.stdout, process.stdout);
    forwardOutput(apiServer.stderr, process.stderr);
    await waitForUrl({
      process: apiServer,
      url: apiHealthUrl,
      label: "FastAPI E2E server",
      validate: async (response) => (await response.json()).status === "ok",
    });
  }

  webServer = spawn(
    process.execPath,
    [nextCli, "start", "--hostname", "127.0.0.1", "--port", "3100"],
    { cwd: webRoot, env: process.env, stdio: ["ignore", "pipe", "pipe"] },
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
  await stopServer(webServer);
  await stopServer(apiServer);
}

process.exit(exitCode);
