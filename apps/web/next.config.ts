import type { NextConfig } from "next";

const apiBaseUrl = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  // Allow the bounded university scan to finish through the same-origin proxy.
  experimental: { proxyTimeout: 150_000 },
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${apiBaseUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
