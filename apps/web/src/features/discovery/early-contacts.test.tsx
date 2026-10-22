import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { DiscoveredPaper } from "./contracts";
const api = vi.hoisted(() => ({ lookup: vi.fn() }));
vi.mock("@/lib/api/contact", () => ({ findPublicEmail: api.lookup }));
import { prioritizedAuthors, PaperContactSummary, useEarlyContacts } from "./early-contacts";
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const author = (id: string, corresponding = false) => ({ id, displayName: id, isCorresponding: corresponding, openalexId: null, orcid: null, sourceUrl: "https://openalex.org/A1", institutions: [] });
const paper = (id: string, authors: DiscoveredPaper["authors"]): DiscoveredPaper => ({ id, authors, title: id, openalexId: "W1", doi: null, publicationYear: 2026, publicationDate: null, workType: null, language: null, venue: null, abstractExcerpt: null, evidenceStrength: "title-only", sourceUrl: "https://openalex.org/W1", lastVerifiedAt: "2026-10-11T00:00:00Z", topics: [] });
const response = (id: string) => ({ authorId: id, authorName: id, status: "not-found", emails: [], profiles: [], warnings: [], checkedAt: "2026-10-11T00:00:00Z", pagesChecked: 1, elapsedSeconds: 1, cacheHit: false, lookupUrl: null, verification: "official-profile-evidence-not-deliverability" });

it("checks corresponding authors first, spreads across papers, deduplicates and caps the pass", () => {
  const papers = [paper("p1", [author("a"), author("b", true), author("c"), author("d")]), paper("p2", [author("b"), author("e", true), author("f"), author("g")])];
  expect(prioritizedAuthors(papers)).toEqual(["b", "e", "a", "c", "f", "d"]);
});
it("distinguishes unchecked authors from negative findings", () => {
  render(<PaperContactSummary paper={paper("p", [author("a")])} results={{}} queued={[]} pending={false} />);
  expect(screen.getByText("Authors not checked yet")).toBeInTheDocument();
  expect(screen.queryByText("No public email found in the pages checked")).not.toBeInTheDocument();
});
it("runs only two lookups concurrently and shares completed evidence", async () => {
  const pending: Array<() => void> = [];
  api.lookup.mockImplementation((id: string) => new Promise(resolve => pending.push(() => resolve(response(id)))));
  const papers = [paper("p", [author("a"), author("b"), author("c")])];
  function View() { const task = useEarlyContacts(papers); return <div>{Object.keys(task.results).length} checked</div>; }
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><View /></QueryClientProvider>);
  await waitFor(() => expect(api.lookup).toHaveBeenCalledTimes(2));
  pending.shift()!();
  await waitFor(() => expect(api.lookup).toHaveBeenCalledTimes(3));
  pending.forEach(resolve => resolve());
  await screen.findByText("3 checked");
  expect(client.getQueryData(["research", "public-email-a"])).toMatchObject({ status: "success", data: { authorId: "a" } });
});

it("does not describe a failed check as an absent email", () => {
  render(<PaperContactSummary paper={paper("p", [author("a")])} results={{a: {result: null, error: "Rate limited"}}} queued={[]} pending={false} />);
  expect(screen.getByText("Contact lookup incomplete — review author details")).toBeInTheDocument();
  expect(screen.queryByText("No public email found in the pages checked")).not.toBeInTheDocument();
});
