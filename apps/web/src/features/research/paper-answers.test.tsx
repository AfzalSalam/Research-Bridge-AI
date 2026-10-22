vi.mock("./reading-history", () => ({ ReadingHistory: () => null }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { afterEach, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ readAnswerStatus: vi.fn(), askDocument: vi.fn() }));

vi.mock("@/lib/api/documents", () => api);

import { PaperAnswers } from "./paper-answers";

const status = { enabled: true, provider: "Google Gemini", model: "fixture", disclosure_version: "v1", disclosure: "Questions and paper text are shared.", reserved_calls_today: 0, daily_call_limit: 30, calls_reserved_per_question: 3 };

afterEach(() => { cleanup(); vi.resetAllMocks(); });

function show() {

 const client = new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});

 const onPage=vi.fn();

 render(<QueryClientProvider client={client}><PaperAnswers id="doc" onPage={onPage}/></QueryClientProvider>);

 return {client,onPage};

}

async function fill() { fireEvent.change(await screen.findByLabelText("Your question about the paper"), {target:{value:"What method?"}}); }

it("keeps disabled answers unavailable without a consent form",async()=>{

 api.readAnswerStatus.mockResolvedValue({...status,enabled:false}); show();

 expect(await screen.findByText(/AI answers are not enabled/)).toBeVisible();

 expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();

 expect(api.askDocument).not.toHaveBeenCalled();

});

it("requires consent, prevents duplicate clicks and renders safe cited text",async()=>{

 api.readAnswerStatus.mockResolvedValue(status);

 api.askDocument.mockResolvedValue({status:"answer",notice:"Check the original.",claims:[{text:"<script>claim</script>",citations:[{page:2,start:0,end:8,quote:"Evidence"}]}]});

 const {onPage}=show(); await fill();

 expect(screen.getByRole("checkbox")).not.toBeChecked();

 fireEvent.click(screen.getByRole("button",{name:"Ask the paper"}));

 expect(await screen.findByRole("alert")).toHaveTextContent("Review and accept");

 expect(api.askDocument).not.toHaveBeenCalled();

 fireEvent.click(screen.getByRole("checkbox"));

 fireEvent.click(screen.getByRole("button",{name:"Ask the paper"}));

 expect(await screen.findByText("<script>claim</script>")).toBeVisible();

 expect(document.querySelector("script")).toBeNull();

 expect(api.askDocument).toHaveBeenCalledWith("doc","What method?","v1",expect.any(String));

 fireEvent.click(screen.getByRole("button",{name:"Read cited page 2"})); expect(onPage).toHaveBeenCalledWith(2);

});

it("resets consent when disclosure changes",async()=>{

 api.readAnswerStatus.mockResolvedValue(status); const {client}=show(); await fill();

 fireEvent.click(screen.getByRole("checkbox"));

 client.setQueryData(["paper-answer-status","doc"],{...status,disclosure_version:"v2"});

 await vi.waitFor(()=>expect(screen.getByRole("checkbox")).not.toBeChecked());

});

it("blocks requests when the daily allowance is exhausted",async()=>{

 api.readAnswerStatus.mockResolvedValue({...status,reserved_calls_today:30});show();

 expect(await screen.findByRole("button",{name:"Ask the paper"})).toBeDisabled();

 expect(api.askDocument).not.toHaveBeenCalled();

});

it.each(["insufficient_evidence","unavailable"])("shows %s without a fabricated answer",async outcome=>{

 api.readAnswerStatus.mockResolvedValue(status); api.askDocument.mockResolvedValue({status:outcome,claims:[],notice:"Limited excerpts."});show();await fill();

 fireEvent.click(screen.getByRole("checkbox"));fireEvent.click(screen.getByRole("button",{name:"Ask the paper"}));

 expect(await screen.findByText(outcome==="unavailable" ? /answer could not be completed/ : /enough supported evidence/)).toBeVisible();

});

it("does not automatically retry a failed request",async()=>{

 api.readAnswerStatus.mockResolvedValue(status);api.askDocument.mockRejectedValue(new Error("Quota unavailable"));show();await fill();

 fireEvent.click(screen.getByRole("checkbox"));fireEvent.click(screen.getByRole("button",{name:"Ask the paper"}));

 expect(await screen.findByRole("alert")).toHaveTextContent("No automatic retry");

 expect(api.askDocument).toHaveBeenCalledTimes(1);

});



it("sends only one request for repeated clicks while pending",async()=>{

 api.readAnswerStatus.mockResolvedValue(status);api.askDocument.mockReturnValue(new Promise(()=>{}));show();await fill();

 fireEvent.click(screen.getByRole("checkbox"));

 const button=screen.getByRole("button",{name:"Ask the paper"});fireEvent.click(button);fireEvent.click(button);

 await vi.waitFor(()=>expect(api.askDocument).toHaveBeenCalledTimes(1));

 expect(await screen.findByRole("button",{name:/Checking the paper/})).toBeDisabled();

});

