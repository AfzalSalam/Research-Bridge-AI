import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
const search = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/documents", () => ({ searchDocumentPassages: search, searchSemanticPassages: search }));
import { PassageSearch } from "./passage-search";
afterEach(() => { cleanup(); vi.resetAllMocks(); });
function show(onPage = vi.fn()) {
 render(<QueryClientProvider client={new QueryClient()}><PassageSearch id="doc" onPage={onPage}/></QueryClientProvider>);
 return onPage;
}
function submit() {
 fireEvent.change(screen.getByLabelText("Topic or keywords"), { target: { value: "graph method" } });
 fireEvent.click(screen.getByRole("button", { name: "Find passages" }));
}
it("renders excerpts safely and opens their source page", async () => {
 search.mockResolvedValue({ passages: [{ page: 2, start: 0, end: 30, text: "<script>source text</script>" }] });
 const open = show(); submit();
 expect(await screen.findByText("<script>source text</script>")).toBeInTheDocument();
 expect(document.querySelector("script")).toBeNull();
 fireEvent.click(screen.getByRole("button", { name: "Read page 2" }));
 expect(open).toHaveBeenCalledWith(2);
 expect(search).toHaveBeenCalledWith("doc", "graph method");
});
it("explains no matches without claiming the question is unanswerable", async () => {
 search.mockResolvedValue({ passages: [] }); show(); submit();
 expect(await screen.findByText(/This does not prove the paper/)).toBeInTheDocument();
});
it("shows a request failure and allows another search", async () => {
 search.mockRejectedValue(new Error("Temporary failure")); show(); submit();
 expect(await screen.findByRole("alert")).toHaveTextContent("Temporary failure");
 expect(screen.getByRole("button", { name: "Find passages" })).toBeEnabled();
});

it("requires unchecked semantic consent before sending and links source pages", async () => {
 search.mockResolvedValue({ passages: [{ page: 3, start: 0, end: 8, text: "Evidence" }] });
 const open = vi.fn();
 render(<QueryClientProvider client={new QueryClient()}><PassageSearch id="doc" onPage={open} semantic/></QueryClientProvider>);
 expect(screen.getByRole("checkbox")).not.toBeChecked();
 fireEvent.change(screen.getByLabelText("Question or topic"), { target: { value: "What method?" } });
 fireEvent.click(screen.getByRole("button", { name: "Search by meaning" }));
 expect(await screen.findByRole("alert")).toHaveTextContent("Review and accept");
 expect(search).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole("checkbox"));
 fireEvent.click(screen.getByRole("button", { name: "Search by meaning" }));
 expect(await screen.findByText("Evidence")).toBeInTheDocument();
 expect(search).toHaveBeenCalledWith("doc", "What method?", "paper-query-embeddings-v1");
 fireEvent.click(screen.getByRole("button", { name: "Read page 3" }));
 expect(open).toHaveBeenCalledWith(3);
});


it("discloses Gemini and submits its explicit query consent", async () => {
 search.mockResolvedValue({ passages: [] });
 render(<QueryClientProvider client={new QueryClient()}><PassageSearch id="doc" onPage={vi.fn()} semantic provider="Google Gemini" disclosureVersion="paper-query-gemini-v1"/></QueryClientProvider>);
 expect(screen.getByText(/Google may use free-tier/)).toBeVisible();
 expect(screen.getByRole("checkbox")).not.toBeChecked();
 fireEvent.change(screen.getByLabelText("Question or topic"), { target: { value: "public question" } });
 fireEvent.click(screen.getByRole("checkbox"));
 fireEvent.click(screen.getByRole("button", { name: "Search by meaning" }));
 await vi.waitFor(() => expect(search).toHaveBeenCalledWith("doc", "public question", "paper-query-gemini-v1"));
});
