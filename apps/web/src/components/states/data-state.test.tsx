import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DataState } from "@/components/states/data-state";

describe("DataState", () => {
  afterEach(cleanup);

  it("announces loading state and exposes busy semantics", () => {
    render(
      <DataState
        description="Academic sources are still responding."
        kind="loading"
        title="Gathering evidence"
      />,
    );

    const status = screen.getByRole("status", { name: "Gathering evidence" });

    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveTextContent("Loading");
    expect(status).toHaveTextContent("Academic sources are still responding.");
  });

  it("announces an error assertively", () => {
    render(
      <DataState
        description="Try the request again."
        kind="error"
        title="Evidence could not be loaded"
      />,
    );

    expect(
      screen.getByRole("alert", { name: "Evidence could not be loaded" }),
    ).toHaveTextContent("Action needed");
  });

  it("labels partial evidence without presenting it as a failure", () => {
    render(
      <DataState
        description="OpenAlex responded while another source timed out."
        kind="partial"
        title="Some evidence is available"
      />,
    );

    expect(screen.getByText("Partial result")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
