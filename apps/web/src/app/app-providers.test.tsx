import { useQueryClient } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";

import { AppProviders } from "@/app/app-providers";

const identity = vi.hoisted(() => ({ id: "account-a" }));
vi.mock("@/features/auth/use-auth", () => ({ useAuth: () => ({ user: identity.id ? { id: identity.id } : null, loading: false }) }));
vi.mock("@/lib/api/setup", () => ({ configureApiClient: vi.fn() }));
vi.mock("@/features/demo/demo-store", () => ({ DemoProvider: ({ children }: { children: ReactNode }) => children }));
vi.mock("@/features/theme/theme-provider", () => ({ ThemeProvider: ({ children }: { children: ReactNode }) => children }));

function PrivateWorkspace() {
  const client = useQueryClient();
  const [draft, setDraft] = useState("");
  return <>
    <p>{client.getQueryData<string>(["private-test"]) ?? "Empty cache"}</p>
    <p>{draft || "No local draft"}</p>
    <button onClick={() => { client.setQueryData(["private-test"], "Asha's research"); setDraft("Asha's draft"); }}>Save private state</button>
  </>;
}

afterEach(cleanup);
it("clears cached and local private state when identity changes or signs out", () => {
  identity.id = "account-a";
  const { rerender } = render(<AppProviders><PrivateWorkspace /></AppProviders>);
  fireEvent.click(screen.getByRole("button", { name: "Save private state" }));
  expect(screen.getByText("Asha's research")).toBeInTheDocument();
  identity.id = "account-b";
  rerender(<AppProviders><PrivateWorkspace /></AppProviders>);
  expect(screen.getByText("Empty cache")).toBeInTheDocument();
  expect(screen.getByText("No local draft")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Save private state" }));
  identity.id = "";
  rerender(<AppProviders><PrivateWorkspace /></AppProviders>);
  expect(screen.queryByText("Asha's research")).not.toBeInTheDocument();
  expect(screen.queryByText("Asha's draft")).not.toBeInTheDocument();
});
