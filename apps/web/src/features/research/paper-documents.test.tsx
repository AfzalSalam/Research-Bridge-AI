vi.mock("./reading-history", () => ({ ReadingHistory: () => null }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ listDocuments: vi.fn(), uploadDocument: vi.fn(), deleteDocument: vi.fn(), readDocumentPages: vi.fn(), readAnswerStatus: vi.fn().mockResolvedValue({enabled:false}), readIndexStatus: vi.fn() }));
vi.mock("@/lib/api/documents", () => api);
import { PaperDocuments } from "./paper-documents";
afterEach(() => { cleanup(); vi.resetAllMocks(); });
function show() { render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}><PaperDocuments paperId="paper"/></QueryClientProvider>); }
it("explains disabled setup without allowing uploads", async () => {
 api.listDocuments.mockResolvedValue({ uploads_enabled: false, documents: [] }); show();
 expect(await screen.findByText(/PDF uploads are not enabled yet/)).toBeInTheDocument();
 expect(screen.queryByRole("button", { name: "Upload PDF" })).not.toBeInTheDocument();
});
it("allows selected PDF upload and refreshes documents", async () => {
 api.listDocuments.mockResolvedValue({ uploads_enabled: true, documents: [] }); api.uploadDocument.mockResolvedValue({ id: "doc" }); show();
 const input = await screen.findByLabelText("Choose a PDF");
 const file = new File(["%PDF-fixture"], "paper.pdf", { type: "application/pdf" });
 fireEvent.change(input, { target: { files: [file] } }); fireEvent.click(screen.getByRole("button", { name: "Upload PDF" }));
 await vi.waitFor(() => expect(api.uploadDocument).toHaveBeenCalledWith("paper", file));
 await vi.waitFor(() => expect(api.listDocuments.mock.calls.length).toBeGreaterThan(1));
});
it("shows safe page text only for ready documents", async () => {
 api.listDocuments.mockResolvedValue({ uploads_enabled: true, documents: [{id:"doc",filename:"paper.pdf",status:"ready",reason:null,warnings:[]}] });
 api.readAnswerStatus.mockResolvedValue({enabled:false}); api.readIndexStatus.mockResolvedValue({enabled:false,status:"not_started"});
 api.readDocumentPages.mockResolvedValue([{ number: 1, text: "<script>untrusted text</script>" }]); show();
 fireEvent.click(await screen.findByRole("button", { name: "Read extracted pages" }));
 expect(await screen.findByText("<script>untrusted text</script>")).toBeInTheDocument();
 expect(screen.getByLabelText("Extracted paper text").querySelector("script")).toBeNull();
});
