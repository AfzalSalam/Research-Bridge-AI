import { beforeEach, describe, expect, it, vi } from "vitest";

const generated = vi.hoisted(() => ({
  bootstrap: vi.fn(),
  discovery: vi.fn(),
  draft: vi.fn(),
  updateProfile: vi.fn(),
  setConfig: vi.fn(),
}));

vi.mock("@/lib/api/generated/client.gen", () => ({
  client: { setConfig: generated.setConfig },
}));

vi.mock("@/lib/api/generated", () => ({
  Sdk: class {
    readDemoBootstrapApiV1DemoBootstrapGet = generated.bootstrap;
    runDemoDiscoveryApiV1DemoDiscoveryPost = generated.discovery;
    createDemoOutreachDraftApiV1DemoOutreachDraftsPost = generated.draft;
    updateDemoProfileApiV1DemoProfilePut = generated.updateProfile;
  },
}));

import {
  createDemoOutreachDraft,
  DemoApiError,
  getDemoBootstrap,
  runDemoDiscovery,
  updateDemoProfile,
} from "@/lib/api/demo";

const profile = {
  id: "demo-student" as const,
  name: "Aarav Demo",
  program: "B.Tech in Computer Science",
  institution: "Example Engineering College (fictional)",
  graduationYear: "2027",
  researchInterests: ["human-centred AI"],
  skills: ["Python"],
  projectTitle: "Uncertainty-aware clinical interface",
  projectSummary:
    "Built a classroom prototype that makes model uncertainty visible to community health workers.",
  weeklyAvailability: "10-15 hours" as const,
};

const paper = {
  id: "paper-one",
  title: "Context Before Confidence",
  authors: ["Mira Sen"],
  year: 2025,
  venue: "Fictional Research Symposium",
  summary: "A fictional abstract about uncertainty-aware clinical interfaces.",
  topics: ["human-centred AI"],
  evidenceStrength: "full-abstract" as const,
  sourceUrl: "https://example.org/papers/one",
};

const mentor = {
  id: "mentor-one",
  name: "Dr. Mira Sen (fictional)",
  role: "Associate Professor",
  department: "Human-Centred Computing",
  institution: "Example Institute (fictional)",
  location: "Location unknown",
  researchThemes: ["human-centred AI"],
  fitRationale: ["The selected topic overlaps with the paper evidence."],
  identityNote: "This record is fictional and no identity resolution was attempted.",
  sourceUrl: "https://example.org/mentors/one",
  papers: [paper],
};

const bootstrap = {
  schemaVersion: 1 as const,
  mode: "fictional-demo" as const,
  defaultQuery: "human-centred AI for community clinics",
  profile,
  mentors: [mentor],
  opportunities: [
    {
      id: "opportunity-one",
      title: "Student Research Assistant",
      organisation: "Example Institute (fictional)",
      location: "Location unknown",
      mode: "Unknown" as const,
      funding: "Unknown" as const,
      availability: "Open" as const,
      deadline: null,
      description: "A fictional opportunity for evaluating clinical interfaces.",
      topics: ["human-centred AI"],
      sourceUrl: "https://example.org/opportunities/one",
      lastVerifiedAt: "2026-08-01T09:30:00Z",
    },
  ],
};

describe("typed demo API adapter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("runtime-validates a generated bootstrap response", async () => {
    generated.bootstrap.mockResolvedValue({
      data: bootstrap,
      error: undefined,
      response: new Response(null, { status: 200 }),
    });

    await expect(getDemoBootstrap()).resolves.toEqual(bootstrap);
  });

  it("saves a profile through the generated client and validates the response", async () => {
    const updated = { ...profile, name: "Riya Demo" };
    generated.updateProfile.mockResolvedValue({
      data: updated,
      error: undefined,
      response: new Response(null, { status: 200 }),
    });

    await expect(updateDemoProfile(updated)).resolves.toEqual(updated);
    expect(generated.updateProfile).toHaveBeenCalledWith({
      body: updated,
      signal: undefined,
    });
  });

  it("preserves structured API failures and request references", async () => {
    generated.discovery.mockResolvedValue({
      data: undefined,
      error: {
        error: {
          code: "demo_source_unavailable",
          message: "The fictional source did not respond.",
          requestId: "request-test-42",
          details: [],
        },
      },
      response: new Response(null, { status: 503 }),
    });

    const promise = runDemoDiscovery({
      query: "human-centred AI for clinics",
      scenario: "error",
    });
    await expect(promise).rejects.toMatchObject({
      code: "demo_source_unavailable",
      requestId: "request-test-42",
      status: 503,
    });
    await expect(promise).rejects.toBeInstanceOf(DemoApiError);
  });

  it("rejects successful bytes that violate the runtime contract", async () => {
    generated.bootstrap.mockResolvedValue({
      data: { ...bootstrap, mode: "live" },
      error: undefined,
      response: new Response(null, {
        headers: { "X-Request-ID": "contract-test-9" },
        status: 200,
      }),
    });

    await expect(getDemoBootstrap()).rejects.toMatchObject({
      code: "contract_mismatch",
      requestId: "contract-test-9",
    });
  });

  it("sends only the selected profile, mentor, and papers for draft creation", async () => {
    generated.draft.mockResolvedValue({
      data: {
        id: "draft-mentor-one",
        mentorId: "mentor-one",
        paperIds: ["paper-one"],
        subject: "Prospective student interested in human-centred AI",
        body: "Dear Dr. Mira Sen,\n\nThis deterministic test body is intentionally long enough to satisfy the validated outreach contract before human review.",
        selectedStudentFacts: ["profile.name"],
        claimEvidence: [
          { claim: "Reference to Context Before Confidence", evidenceIds: ["paper-one"] },
        ],
        uncertaintyWarnings: ["Availability and contact details are unknown."],
        generatedAt: "2026-08-01T09:30:00Z",
        updatedAt: "2026-08-01T09:30:00Z",
        mode: "deterministic-demo",
        templateVersion: "phase-04.v1",
        draftVersion: 1,
        evidenceLinks: [
          "https://example.org/mentors/one",
          "https://example.org/papers/one",
        ],
      },
      error: undefined,
      response: new Response(null, { status: 201 }),
    });

    await createDemoOutreachDraft({
      mentorId: "mentor-one",
      paperIds: ["paper-one"],
      profile,
    });

    expect(generated.draft).toHaveBeenCalledWith({
      body: {
        mentorId: "mentor-one",
        paperIds: ["paper-one"],
        profile,
      },
      signal: undefined,
    });
  });
});
