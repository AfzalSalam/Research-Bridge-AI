import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ readIndexStatus: vi.fn(), startDocumentIndex: vi.fn(), cancelDocumentIndex: vi.fn() }));
vi.mock("@/lib/api/documents", () => api);
import { DocumentIndexing } from "./document-indexing";
afterEach(() => { cleanup(); vi.resetAllMocks(); });
function show() { render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><DocumentIndexing id="doc"/></QueryClientProvider>); }
it("requires unchecked explicit consent before queueing", async () => {
 api.readIndexStatus.mockResolvedValue({ enabled: true, status: "not_started", disclosure_version: "paper-embeddings-v1" });
 api.startDocumentIndex.mockResolvedValue({id:"job"}); show();
 const button = await screen.findByRole("button", { name: "Prepare this paper" });
 const checkbox = screen.getByRole("checkbox");
 expect(checkbox).not.toBeChecked(); fireEvent.click(button);
 expect(await screen.findByRole("alert")).toHaveTextContent("review and accept");
 expect(api.startDocumentIndex).not.toHaveBeenCalled();
 fireEvent.click(checkbox); fireEvent.click(button);
 await vi.waitFor(() => expect(api.startDocumentIndex).toHaveBeenCalledWith("doc", "paper-embeddings-v1"));
});
it("does not offer submission when disabled", async () => {
 api.readIndexStatus.mockResolvedValue({ enabled: false, status: "not_started" }); show();
 expect(await screen.findByText(/not enabled yet/)).toBeVisible();
 expect(screen.queryByRole("checkbox")).toBeNull();
});
it("allows cancelling queued work and explains in-flight limitations", async () => {
 api.readIndexStatus.mockResolvedValue({ enabled: true, status: "queued" });
 api.cancelDocumentIndex.mockResolvedValue(null); show();
 fireEvent.click(await screen.findByRole("button", { name: "Cancel preparation" }));
 await vi.waitFor(() => expect(api.cancelDocumentIndex).toHaveBeenCalledWith("doc"));
 expect(screen.getByText(/cannot be recalled/)).toBeVisible();
});


it("clears prior consent when the provider changes", async () => {
 const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
 api.readIndexStatus.mockResolvedValue({ enabled: true, status: "not_started", provider: "OpenAI", disclosure_version: "paper-embeddings-v1" });
 render(<QueryClientProvider client={client}><DocumentIndexing id="doc"/></QueryClientProvider>);
 fireEvent.click(await screen.findByRole("checkbox"));
 expect(screen.getByRole("checkbox")).toBeChecked();
 client.setQueryData(["document-index", "doc"], { enabled: true, status: "not_started", provider: "Google Gemini", disclosure_version: "paper-gemini-v1" });
 await vi.waitFor(() => expect(screen.getByRole("checkbox")).not.toBeChecked());
 expect(screen.getByText(/Google may use free-tier/)).toBeVisible();
 fireEvent.click(screen.getByRole("button", { name: "Prepare this paper" }));
 expect(await screen.findByRole("alert")).toHaveTextContent("review and accept");
 expect(api.startDocumentIndex).not.toHaveBeenCalled();
});
