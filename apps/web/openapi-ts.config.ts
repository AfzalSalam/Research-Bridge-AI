import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "../api/openapi.json",
  output: {
    path: "src/lib/api/generated",
    tsConfigPath: "./tsconfig.json",
  },
  plugins: [
    "@hey-api/typescript",
    "@hey-api/client-fetch",
    {
      name: "@hey-api/sdk",
      operations: {
        strategy: "single",
      },
    },
  ],
});
