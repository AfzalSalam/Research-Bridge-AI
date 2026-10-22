import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { UniversityDiscovery } from "./university-discovery";
import type { ScanSnapshot } from "./university-contracts";
import { scanUniversityWebsites } from "@/lib/api/university";

vi.mock("@/lib/api/university", () => ({ scanUniversityWebsites: vi.fn() }));
const result: ScanSnapshot = {
  state: "partial", query: "machine learning", target: 30, papers: [], sources: [],
  pagesAttempted: 2, pagesRead: 1, elapsedSeconds: 4, budgetSeconds: 120,
  currentUniversity: null, stopReason: "reviewed_links_exhausted", warnings: ["One source unavailable."],
  programs: [{ university: "OIST", name: "Research internship", sourceUrl: "https://www.oist.jp/",
    checkedAt: "2026-10-09T00:00:00Z", status: "not-confirmed", deadline: null,
    statusEvidence: null, workMode: "not-specified", workModeEvidence: null,
    eligibilityEvidence: null, applicationNote: "Use the official application portal." }],
};
function show() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><UniversityDiscovery /></QueryClientProvider>);
}
beforeEach(() => { vi.mocked(scanUniversityWebsites).mockReset(); });
afterEach(cleanup);

it("submits the chosen paper target and keeps unknown work mode explicit", async () => {
  vi.mocked(scanUniversityWebsites).mockImplementation(async (_form, _signal, emit) => { emit(result); });
  show();
  fireEvent.change(screen.getByLabelText("Number of papers"), { target: { value: "30" } });
  fireEvent.click(screen.getByRole("button", { name: "Scan university websites" }));
  await screen.findByText("Found 0 of 30 requested papers");
  expect(vi.mocked(scanUniversityWebsites).mock.calls[0][0].target).toBe("30");
  expect(screen.getByText(/Application status not confirmed/)).toBeVisible();
  expect(screen.getByText(/Work mode is not explicitly established/)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Internship work mode"), { target: { value: "remote" } });
  await waitFor(() => expect(screen.queryByText("OIST — Research internship")).not.toBeInTheDocument());
  expect(screen.getByText(/No verified program evidence matches/)).toBeVisible();
});

it("cancels an active scan and retains already extracted evidence", async () => {
  vi.mocked(scanUniversityWebsites).mockImplementation(async (_form, signal, emit) => {
    emit({ ...result, state: "scanning" });
    await new Promise<void>((resolve) => signal.addEventListener("abort", () => resolve(), { once: true }));
  });
  show();
  fireEvent.click(screen.getByRole("button", { name: "Scan university websites" }));
  fireEvent.click(await screen.findByRole("button", { name: "Cancel scan" }));
  await screen.findByText(/Scan cancelled/);
  expect(screen.getByText("Found 0 of 30 requested papers")).toBeVisible();
  expect(vi.mocked(scanUniversityWebsites).mock.calls[0][1].aborted).toBe(true);
});

it("retains partial evidence when a later stream error occurs", async () => {
  vi.mocked(scanUniversityWebsites).mockImplementation(async (_form, _signal, emit) => {
    emit({ ...result, state: "scanning" });
    throw new Error("The scan connection ended early.");
  });
  show();
  fireEvent.click(screen.getByRole("button", { name: "Scan university websites" }));
  await screen.findByRole("alert");
  expect(screen.getByText("Found 0 of 30 requested papers")).toBeVisible();
});
