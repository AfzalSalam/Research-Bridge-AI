import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
const read = vi.hoisted(()=>vi.fn());
vi.mock("@/lib/api/documents",()=>({readReadingHistory:read}));
import { ReadingHistory } from "./reading-history";
afterEach(()=>{cleanup();vi.resetAllMocks();});
function show(onPage=vi.fn()) {return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ReadingHistory id="doc" onPage={onPage}/></QueryClientProvider>);}
it("loads saved questions and navigates their citations without generating",async()=>{
 read.mockResolvedValue([{id:"entry",question:"Saved question",model:"fixture",created_at:"2026-10-22T00:00:00Z",result:{status:"answer",notice:"Excerpts only",claims:[{text:"<script>claim</script>",citations:[{page:2,quote:"Original evidence"}]}]}}]);
 const onPage=vi.fn();show(onPage);
 fireEvent.click(await screen.findByText("Saved question"));
 expect(screen.getByText("<script>claim</script>")).toBeVisible();
 expect(document.querySelector("script")).toBeNull();
 fireEvent.click(screen.getByRole("button",{name:"Read saved cited page 2"}));
 expect(onPage).toHaveBeenCalledWith(2);
 expect(read).toHaveBeenCalledWith("doc");
});
it("shows an empty history",async()=>{read.mockResolvedValue([]);show();expect(await screen.findByText("No saved questions yet.")).toBeVisible();});
it("offers an explicit retry after failure",async()=>{read.mockRejectedValue(new Error("unavailable"));show();fireEvent.click(await screen.findByRole("button",{name:"Retry history"}));await vi.waitFor(()=>expect(read).toHaveBeenCalledTimes(2));});
