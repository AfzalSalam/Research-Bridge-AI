import { createClient } from "@hey-api/openapi-ts";
import { mkdtemp, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const input = path.resolve(webRoot, "../api/openapi.json");
const committedOutput = path.resolve(webRoot, "src/lib/api/generated");
const checkOnly = process.argv.includes("--check");
const temporaryRoot = checkOnly
  ? await mkdtemp(path.join(tmpdir(), "research-bridge-openapi-"))
  : null;
const outputPath = temporaryRoot ?? committedOutput;

async function filesBelow(root, current = root) {
  const entries = await readdir(current, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const absolute = path.join(current, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await filesBelow(root, absolute)));
    } else {
      files.push(path.relative(root, absolute).replaceAll("\\", "/"));
    }
  }
  return files.sort();
}

async function compareDirectories(expected, actual) {
  const [expectedFiles, actualFiles] = await Promise.all([
    filesBelow(expected),
    filesBelow(actual),
  ]);
  if (JSON.stringify(expectedFiles) !== JSON.stringify(actualFiles)) return false;

  for (const relativePath of expectedFiles) {
    const [expectedContent, actualContent] = await Promise.all([
      readFile(path.join(expected, relativePath)),
      readFile(path.join(actual, relativePath)),
    ]);
    if (!expectedContent.equals(actualContent)) return false;
  }
  return true;
}

async function normalizeGeneratedFiles(root) {
  for (const relativePath of await filesBelow(root)) {
    const absolutePath = path.join(root, relativePath);
    const content = await readFile(absolutePath, "utf8");
    const normalized = content.replace(/[\t ]+$/gm, "");
    if (normalized !== content) {
      await writeFile(absolutePath, normalized, "utf8");
    }
  }
}

try {
  await createClient({
    input,
    output: {
      path: outputPath,
      tsConfigPath: path.resolve(webRoot, "tsconfig.json"),
    },
    plugins: [
      "@hey-api/typescript",
      "@hey-api/client-fetch",
      { name: "@hey-api/sdk", operations: { strategy: "single" } },
    ],
  });
  await normalizeGeneratedFiles(outputPath);

  if (checkOnly) {
    const current = await compareDirectories(temporaryRoot, committedOutput);
    if (!current) {
      console.error("Generated API client is stale; run: npm run api:generate");
      process.exitCode = 1;
    } else {
      console.log("Generated API client matches apps/api/openapi.json.");
    }
  }
} finally {
  if (temporaryRoot) {
    await rm(temporaryRoot, { force: true, recursive: true });
  }
}
