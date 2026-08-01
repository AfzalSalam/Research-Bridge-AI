import { describe, expect, it } from "vitest";

import { studentProfileSchema } from "@/features/demo/contracts";
import { demoReducer } from "@/features/demo/demo-reducer";
import { createInitialDemoState } from "@/features/demo/demo-reducer";

const profile = studentProfileSchema.parse({
  id: "demo-student",
  name: "Aarav Demo",
  program: "B.Tech in Computer Science, fourth year",
  institution: "Riverview College of Engineering (fictional)",
  graduationYear: "2027",
  researchInterests: ["human-centred AI"],
  skills: ["Python"],
  projectTitle: "Uncertainty-aware triage interface",
  projectSummary:
    "Built a classroom prototype that surfaces model uncertainty for community health workers.",
  weeklyAvailability: "10-15 hours",
});

describe("demoReducer", () => {
  it("keeps paper selections scoped to a mentor", () => {
    const initial = createInitialDemoState(profile);
    const selected = demoReducer(initial, {
      type: "toggle-paper",
      mentorId: "mentor-mira-sen",
      paperId: "paper-context-before-confidence",
    });

    expect(selected?.selectedPaperIds["mentor-mira-sen"]).toEqual([
      "paper-context-before-confidence",
    ]);
    expect(initial.selectedPaperIds).toEqual({});
  });

  it("resets all session mutations to the canonical fixture state", () => {
    const initial = createInitialDemoState(profile);
    const mutated = demoReducer(initial, {
      type: "toggle-opportunity",
      opportunityId: "opp-northstar-hcai",
    });

    expect(mutated?.savedOpportunityIds).toHaveLength(1);
    expect(demoReducer(mutated, { type: "reset", profile })).toEqual(initial);
  });
});
