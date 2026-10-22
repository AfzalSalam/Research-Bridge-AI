import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
const read = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/documents", () => ({ readOriginalPdf: read }));
import { OriginalPdf } from "./original-pdf";
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.resetAllMocks(); });
function show() {
 return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><OriginalPdf id="doc"/></QueryClientProvider>);
}
it("revokes temporary PDF access on unmount", async () => {
 const revoke = vi.fn();
 const original = URL;
 class TestURL extends original { static createObjectURL = vi.fn(() => "blob:private-pdf"); static revokeObjectURL = revoke; }
 vi.stubGlobal("URL", TestURL);
 read.mockResolvedValue(new Blob(["%PDF-fixture"], { type: "application/pdf" }));
 const view = show();
 expect(await screen.findByRole("link", { name: "Download PDF" })).toHaveAttribute("href", "blob:private-pdf");
 expect(screen.getByTitle("Original paper PDF")).toHaveAttribute("sandbox", "");
 view.unmount();
 expect(revoke).toHaveBeenCalledWith("blob:private-pdf");
});
it("offers retry after a failed request", async () => {
 read.mockRejectedValue(new Error("Storage unavailable")); show();
 expect(await screen.findByRole("alert")).toHaveTextContent("Storage unavailable");
 fireEvent.click(screen.getByRole("button", { name: "Retry PDF" }));
 await vi.waitFor(() => expect(read).toHaveBeenCalledTimes(2));
});
it("aborts a pending request when the reader closes", async () => {
 let signal: AbortSignal | undefined;
 read.mockImplementation((_id: string, current: AbortSignal) => { signal = current; return new Promise(() => {}); });
 const view = show();
 await vi.waitFor(() => expect(signal).toBeDefined());
 view.unmount();
 expect(signal?.aborted).toBe(true);
});

it("updates the requested PDF page without fetching the file again", async () => {
 const revoke = vi.fn();
 const original = URL;
 class TestURL extends original { static createObjectURL = vi.fn(() => "blob:private-pdf"); static revokeObjectURL = revoke; }
 vi.stubGlobal("URL", TestURL);
 read.mockResolvedValue(new Blob(["%PDF-fixture"], { type: "application/pdf" }));
 const client = new QueryClient({defaultOptions:{queries:{retry:false}}});
 const reader = (page:number) => <QueryClientProvider client={client}><OriginalPdf id="doc" page={page}/></QueryClientProvider>;
 const view = render(reader(1));
 expect(await screen.findByTitle("Original paper PDF")).toHaveAttribute("src", "blob:private-pdf#page=1");
 view.rerender(reader(3));
 expect(screen.getByTitle("Original paper PDF")).toHaveAttribute("src", "blob:private-pdf#page=3");
 expect(read).toHaveBeenCalledTimes(1);
 expect(revoke).toHaveBeenCalledWith("blob:private-pdf");
 view.rerender(reader(-1));
 expect(screen.getByTitle("Original paper PDF")).toHaveAttribute("src", "blob:private-pdf#page=1");
});
