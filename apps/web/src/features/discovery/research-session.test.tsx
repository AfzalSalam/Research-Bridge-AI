import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { z } from "zod";
import { ResearchSessionProvider, useResearchTask, useResearchValue } from "./research-session";

const execute = vi.fn<(values: { query: string }, signal: AbortSignal, emit: (result: { text: string }) => void) => Promise<{ text: string } | void>>();
function Search() {
  const task = useResearchTask("test-search", z.object({ text: z.string() }), z.object({ query: z.string() }), execute);
  return <><p>{task.status}</p><p>{task.data?.text ?? "No evidence"}</p><button onClick={() => task.mutate({ query: "robotics" })}>Search</button><button onClick={task.clear}>Clear</button></>;
}
function Workspace({ client, visible = true, identity = "account-a" }: { client: QueryClient; visible?: boolean; identity?: string }) {
  return <QueryClientProvider client={client}><ResearchSessionProvider key={identity} identity={identity}>{visible ? <Search /> : <p>Other page</p>}</ResearchSessionProvider></QueryClientProvider>;
}
beforeEach(() => { sessionStorage.clear(); execute.mockReset(); });
afterEach(cleanup);

it("keeps in-flight work alive during navigation and restores its results", async () => {
  let finish: (value: { text: string }) => void = () => {};
  execute.mockImplementation(async () => new Promise((resolve) => { finish = resolve; }));
  const client = new QueryClient();
  const view = render(<Workspace client={client} />);
  fireEvent.click(screen.getByText("Search"));
  await screen.findByText("pending");
  const signal = execute.mock.calls[0][1];
  view.rerender(<Workspace client={client} visible={false} />);
  expect(signal.aborted).toBe(false);
  finish({ text: "Retained publication" });
  view.rerender(<Workspace client={client} />);
  await screen.findByText("Retained publication");
  view.unmount();
  render(<Workspace client={new QueryClient()} />);
  expect(screen.getByText("Retained publication")).toBeVisible();
  expect(execute).toHaveBeenCalledTimes(1);
});

it("restores partial evidence after refresh but never a fictional running scan", async () => {
  execute.mockImplementation(async (_values, signal, emit) => {
    emit({ text: "Partial paper" });
    await new Promise<void>((resolve) => signal.addEventListener("abort", () => resolve(), { once: true }));
  });
  const view = render(<Workspace client={new QueryClient()} />);
  fireEvent.click(screen.getByText("Search"));
  await screen.findByText("Partial paper");
  view.unmount();
  expect(execute.mock.calls[0][1].aborted).toBe(true);
  render(<Workspace client={new QueryClient()} />);
  expect(screen.getByText("interrupted")).toBeVisible();
  expect(screen.getByText("Partial paper")).toBeVisible();
  fireEvent.click(screen.getByText("Clear"));
  await screen.findByText("No evidence");
});

it("rejects malformed snapshots and isolates accounts", async () => {
  sessionStorage.setItem("research-session-v1:account-a", JSON.stringify({ "test-search": { data: { text: 42 }, status: "success" } }));
  execute.mockResolvedValue({ text: "A private search" });
  const view = render(<Workspace client={new QueryClient()} />);
  expect(screen.getByText("No evidence")).toBeVisible();
  fireEvent.click(screen.getByText("Search"));
  await screen.findByText("A private search");
  view.unmount();
  render(<Workspace client={new QueryClient()} identity="account-b" />);
  expect(screen.queryByText("A private search")).not.toBeInTheDocument();
  await waitFor(() => expect(sessionStorage.getItem("research-session-v1:account-a")).toBeNull());
});


it("preserves an explicitly cleared nullable selection after reload", async () => {
  function Selection() {
    const [value, set] = useResearchValue("selection", z.string().nullable(), "first-author");
    return <button onClick={() => set(null)}>{value === null ? "No selection" : value}</button>;
  }
  function View() {
    return <QueryClientProvider client={new QueryClient()}><ResearchSessionProvider identity="account-a"><Selection /></ResearchSessionProvider></QueryClientProvider>;
  }
  const view = render(<View />);
  fireEvent.click(screen.getByText("first-author"));
  await screen.findByText("No selection");
  view.unmount();
  render(<View />);
  expect(screen.getByText("No selection")).toBeVisible();
});
