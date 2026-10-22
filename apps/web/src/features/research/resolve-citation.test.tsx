import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ discover: vi.fn() }));
vi.mock("@/lib/api/discovery", () => ({ discoverOpenAlexPapers: api.discover }));
import { ResolveCitation } from "./resolve-citation";
afterEach(() => { cleanup(); vi.clearAllMocks(); });
function show() {
 const client = new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});
 render(<QueryClientProvider client={client}><ResolveCitation doi={null} publicationUrl="https://arxiv.org/abs/2301.12345v2" /></QueryClientProvider>);
}
it("enables handoff only for an exact canonical DOI", async () => {
 api.discover.mockResolvedValue({papers:[{id:"paper-1",doi:"https://doi.org/10.48550/arXiv.2301.12345"}]});
 show(); fireEvent.click(screen.getByRole("button",{name:"Resolve paper and authors"}));
 expect(await screen.findByRole("link",{name:"Read, save, and contact authors"})).toHaveAttribute("href","/research/papers/paper-1");
 expect(api.discover).toHaveBeenCalledWith(expect.objectContaining({query:"10.48550/arxiv.2301.12345",limit:10}));
});
it("keeps unrelated catalog results unresolved", async () => {
 api.discover.mockResolvedValue({papers:[{id:"wrong-paper",doi:"10.48550/arxiv.2301.99999"}]});
 show(); fireEvent.click(screen.getByRole("button",{name:"Resolve paper and authors"}));
 await screen.findByText(/No exact identifier match/);
 expect(screen.queryByRole("link")).not.toBeInTheDocument();
});
