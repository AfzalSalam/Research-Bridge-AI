import { describe, expect, it } from "vitest";

import { demoReducer } from "@/features/demo/demo-reducer";
import { createInitialDemoState } from "@/features/demo/fixtures";

describe("demoReducer", () => {
  it("keeps paper selections scoped to a mentor", () => {
    const initial = createInitialDemoState();
    const selected = demoReducer(initial, {
      type: "toggle-paper",
      mentorId: "mentor-mira-sen",
      paperId: "paper-context-before-confidence",
    });

    expect(selected.selectedPaperIds["mentor-mira-sen"]).toEqual([
      "paper-context-before-confidence",
    ]);
    expect(initial.selectedPaperIds).toEqual({});
  });

  it("resets all session mutations to the canonical fixture state", () => {
    const initial = createInitialDemoState();
    const mutated = demoReducer(initial, {
      type: "toggle-opportunity",
      opportunityId: "opp-northstar-hcai",
    });

    expect(mutated.savedOpportunityIds).toHaveLength(1);
    expect(demoReducer(mutated, { type: "reset" })).toEqual(initial);
  });
});
