import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/status/status-badge";

describe("StatusBadge", () => {
  afterEach(cleanup);

  it("maps verified evidence to the evidence badge variant", () => {
    render(<StatusBadge tone="evidence">Source verified</StatusBadge>);

    expect(screen.getByText("Source verified").closest("[data-slot=badge]"))
      .toHaveAttribute("data-variant", "evidence");
  });

  it("keeps unknown information visually distinct", () => {
    render(<StatusBadge tone="unknown">Availability unknown</StatusBadge>);

    expect(screen.getByText("Availability unknown").closest("[data-slot=badge]"))
      .toHaveAttribute("data-variant", "unknown");
  });
});
