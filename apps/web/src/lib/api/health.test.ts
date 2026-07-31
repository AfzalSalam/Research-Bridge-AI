import { afterEach, describe, expect, it, vi } from "vitest";

import { getApiHealth } from "@/lib/api/health";

describe("getApiHealth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns validated health data", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ok",
          service: "research-bridge-api",
          version: "0.1.0",
          environment: "test",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getApiHealth({ baseUrl: "http://api.test/" });

    expect(result).toEqual({
      state: "available",
      data: {
        status: "ok",
        service: "research-bridge-api",
        version: "0.1.0",
        environment: "test",
      },
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/v1/health",
      expect.objectContaining({
        cache: "no-store",
        signal: expect.any(AbortSignal),
      }),
    );
  });

  it("rejects a response that does not match the health contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(new Response(JSON.stringify({ status: "ok" }))),
    );

    await expect(
      getApiHealth({ baseUrl: "http://api.test" }),
    ).resolves.toEqual({
      state: "unavailable",
      message: "The API returned an unexpected health response.",
    });
  });
});
