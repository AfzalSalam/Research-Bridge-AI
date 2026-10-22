import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PublicEmailLookup } from "./public-email-lookup";

const lookup = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/contact", () => ({ findPublicEmail: lookup }));
const authorId = "10000000-0000-4000-8000-000000000001";
const result = {
  authorId, authorName: "Mira Sen", status: "found", checkedAt: "2026-10-10T10:00:00Z",
  emails: [{ email: "mira.sen@iitk.ac.in", sourceUrl: "https://www.cse.iitk.ac.in/users/mira/", identityEvidence: ["ORCID matches"], evidenceUrls: ["https://www.cse.iitk.ac.in/users/mira/"], extraction: "mailto", checkedAt: "2026-10-10T10:00:00Z" }],
  profiles: [], warnings: [], pagesChecked: 2, elapsedSeconds: 3, cacheHit: false,
  lookupUrl: null, verification: "official-profile-evidence-not-deliverability",
};
function view() {
  return render(<QueryClientProvider client={new QueryClient()}><PublicEmailLookup authorId={authorId} authorName="Mira Sen" /></QueryClientProvider>);
}
beforeEach(() => {
  lookup.mockReset();
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: vi.fn().mockResolvedValue(undefined) } });
});
afterEach(cleanup);

it("offers a sourced public email for explicit copying, never sending", async () => {
  lookup.mockResolvedValue(result);
  view();
  expect(lookup).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Find public email" }));
  await screen.findByText("mira.sen@iitk.ac.in");
  expect(screen.getByRole("link", { name: /View email on official source/ })).toHaveAttribute("href", result.emails[0].sourceUrl);
  fireEvent.click(screen.getByRole("button", { name: "Copy email" }));
  await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith("mira.sen@iitk.ac.in"));
  expect(screen.queryByRole("button", { name: /^send/i })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Recheck sources" }));
  await waitFor(() => expect(lookup).toHaveBeenLastCalledWith(authorId, { profileUrl: undefined, refresh: true }, expect.any(AbortSignal)));
});

it("shows uncertain profiles without a copyable recipient", async () => {
  lookup.mockResolvedValue({ ...result, status: "needs-review", emails: [], profiles: [{ sourceUrl: result.emails[0].sourceUrl, reason: "Identity is not corroborated" }], warnings: ["One source blocked crawling"] });
  view();
  fireEvent.click(screen.getByRole("button", { name: "Find public email" }));
  await screen.findByText(/Possible profile found/);
  expect(screen.queryByRole("button", { name: "Copy email" })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Review possible official profile/ })).toBeVisible();
});

it("reports errors and lets the student supply a profile URL", async () => {
  lookup.mockRejectedValue(new Error("This domain is not reviewed"));
  view();
  fireEvent.click(screen.getByText("Already found their official profile?"));
  fireEvent.change(screen.getByLabelText("Official profile URL (optional)"), { target: { value: "https://unreviewed.test/person" } });
  fireEvent.click(screen.getByRole("button", { name: "Find public email" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("This domain is not reviewed");
});
