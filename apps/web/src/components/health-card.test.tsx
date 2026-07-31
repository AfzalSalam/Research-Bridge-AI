import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { HealthCard } from "@/components/health-card";

describe("HealthCard", () => {
  afterEach(cleanup);

  it("renders the available API details accessibly", () => {
    render(
      <HealthCard
        result={{
          state: "available",
          data: {
            status: "ok",
            service: "research-bridge-api",
            version: "0.1.0",
            environment: "test",
          },
        }}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("API available");
    expect(screen.getByText("research-bridge-api")).toBeInTheDocument();
    expect(screen.getByText("0.1.0")).toBeInTheDocument();
  });

  it("renders the reason when the API is unavailable", () => {
    render(
      <HealthCard
        result={{
          state: "unavailable",
          message: "The API could not be reached from the frontend server.",
        }}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("API unavailable");
    expect(
      screen.getByText("The API could not be reached from the frontend server."),
    ).toBeInTheDocument();
  });
});
