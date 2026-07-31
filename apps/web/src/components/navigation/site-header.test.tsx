import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SiteHeader } from "@/components/navigation/site-header";

vi.mock("next/navigation", () => ({
  usePathname: () => "/mentors",
}));

describe("SiteHeader", () => {
  afterEach(cleanup);

  it("marks the current route in the desktop navigation", () => {
    render(<SiteHeader />);

    const primaryNavigation = screen.getByRole("navigation", {
      name: "Primary",
    });
    const mentorLink = screen.getByRole("link", { name: "Mentors" });

    expect(primaryNavigation).toContainElement(mentorLink);
    expect(mentorLink).toHaveAttribute("aria-current", "page");
  });

  it("opens a labelled mobile navigation dialog and returns focus on Escape", async () => {
    render(<SiteHeader />);

    const trigger = screen.getByRole("button", { name: "Open navigation" });

    trigger.focus();
    fireEvent.click(trigger);

    const dialog = screen.getByRole("dialog");

    expect(dialog).toHaveAccessibleName(
      "Navigate Research Bridge",
    );
    expect(
      screen.getByRole("navigation", { name: "Mobile" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close navigation" }))
      .toBeInTheDocument();

    fireEvent.keyDown(document, { code: "Escape", key: "Escape" });

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(trigger).toHaveFocus();
  });
});
