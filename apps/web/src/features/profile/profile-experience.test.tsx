import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import { ProfileExperience } from "@/features/profile/profile-experience";
import { ProfileGuard } from "@/features/profile/profile-guard";
import { OnboardingExperience } from "@/features/onboarding/onboarding-experience";
import { accountProfileQueryKey, accountProfileFormSchema, accountProfileToFormValues, getAccountProfile, updateAccountProfile } from "@/lib/api/profile";
import { ApiError } from "@/lib/api/result";
import { accountProfile } from "@/test/fixtures/account-profile";

const identity = vi.hoisted(() => ({ id: "account-a" }));
const navigation = vi.hoisted(() => ({ replace: vi.fn(), pathname: "/profile" }));
vi.mock("@/features/auth/use-auth", () => ({
  useAuth: () => ({ user: { id: identity.id }, loading: false }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => navigation,
  usePathname: () => navigation.pathname,
}));
vi.mock("@/lib/api/profile", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api/profile")>(),
  getAccountProfile: vi.fn(),
  updateAccountProfile: vi.fn(),
}));

function renderAccount(children: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  return { ...render(children, { wrapper }), client };
}

beforeEach(() => {
  identity.id = "account-a";
  navigation.pathname = "/profile";
  navigation.replace.mockReset();
  vi.mocked(getAccountProfile).mockReset().mockResolvedValue(accountProfile);
  vi.mocked(updateAccountProfile).mockReset().mockImplementation(async (profile) => profile);
});
afterEach(cleanup);

describe("account profile editing", () => {
  it("saves real account facts and updates only the signed-in profile cache", async () => {
    const { client } = renderAccount(<ProfileExperience />);
    client.setQueryData(accountProfileQueryKey("account-b"), { ...accountProfile, name: "Other Student" });
    await waitFor(() => expect(screen.getByLabelText("Name")).toHaveValue(accountProfile.name));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Asha Updated" } });
    fireEvent.change(screen.getByLabelText("Research interests"), { target: { value: "clinical AI, human-centred AI" } });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await screen.findByText("Your research profile has been saved.");
    expect(updateAccountProfile).toHaveBeenCalledWith({ ...accountProfile, name: "Asha Updated", researchInterests: ["clinical AI", "human-centred AI"] });
    expect(client.getQueryData(accountProfileQueryKey("account-a"))).toMatchObject({ name: "Asha Updated" });
    expect(client.getQueryData(accountProfileQueryKey("account-b"))).toMatchObject({ name: "Other Student" });
    expect(screen.queryByText(/fictional/i)).not.toBeInTheDocument();
  });

  it("keeps edits and exposes retryable save errors without claiming success", async () => {
    vi.mocked(updateAccountProfile).mockRejectedValue(new ApiError({ code: "unavailable", message: "Please retry saving.", requestId: "profile-test" }));
    renderAccount(<ProfileExperience />);
    await waitFor(() => expect(screen.getByLabelText("Name")).toHaveValue(accountProfile.name));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Unsaved Student" } });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await screen.findByText("Please retry saving. Request reference: profile-test.");
    expect(screen.getByLabelText("Name")).toHaveValue("Unsaved Student");
    expect(screen.queryByText("Your research profile has been saved.")).not.toBeInTheDocument();
  });

  it("rejects empty comma lists and terms longer than the API allows", () => {
    const values = accountProfileToFormValues(accountProfile);
    expect(accountProfileFormSchema.safeParse({ ...values, skills: ", ," }).success).toBe(false);
    expect(accountProfileFormSchema.safeParse({ ...values, researchInterests: "a".repeat(121) }).success).toBe(false);
  });
});

describe("profile guard", () => {
  it("retries a read failure instead of redirecting to onboarding", async () => {
    vi.mocked(getAccountProfile).mockRejectedValueOnce(new Error("Profile service unavailable."));
    renderAccount(<ProfileGuard><p>Private research workspace</p></ProfileGuard>);
    await screen.findByRole("heading", { name: "Your profile is unavailable" });
    expect(navigation.replace).not.toHaveBeenCalled();
    expect(screen.queryByText("Private research workspace")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry profile" }));
    await screen.findByText("Private research workspace");
  });

  it("redirects only a successful missing profile response", async () => {
    vi.mocked(getAccountProfile).mockResolvedValue(null);
    renderAccount(<ProfileGuard><p>Private research workspace</p></ProfileGuard>);
    await waitFor(() => expect(navigation.replace).toHaveBeenCalledWith("/onboarding"));
    expect(screen.queryByText("Private research workspace")).not.toBeInTheDocument();
  });

  it("does not show the previous user's profile during an account switch", async () => {
    const { rerender } = renderAccount(<ProfileExperience />);
    await waitFor(() => expect(screen.getByLabelText("Name")).toHaveValue(accountProfile.name));
    identity.id = "account-b";
    vi.mocked(getAccountProfile).mockImplementation(() => new Promise(() => {}));
    rerender(<ProfileExperience />);
    expect(screen.queryByDisplayValue(accountProfile.name)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Loading your profile" })).toBeInTheDocument();
  });
});

it("onboarding handles a rejected save without navigating or losing input", async () => {
  vi.mocked(updateAccountProfile).mockRejectedValue(new Error("Unable to save profile."));
  renderAccount(<OnboardingExperience />);
  const values = accountProfileToFormValues(accountProfile);
  for (const [field, value] of Object.entries(values)) {
    const input = document.getElementById(field);
    if (!input) throw new Error(`Missing profile field: ${field}`);
    fireEvent.change(input, { target: { value } });
  }
  fireEvent.click(screen.getByRole("button", { name: "Continue to Dashboard" }));
  await screen.findByText("Unable to save profile.");
  expect(navigation.replace).not.toHaveBeenCalled();
  expect(screen.getByLabelText("Full Name")).toHaveValue(accountProfile.name);
});
