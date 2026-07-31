import { describe, expect, it } from "vitest";

import { buildEvidenceGroundedDraft } from "@/features/demo/draft-template";
import { demoMentors, demoProfile } from "@/features/demo/fixtures";

describe("buildEvidenceGroundedDraft", () => {
  it("uses selected profile and paper evidence deterministically", () => {
    const mentor = demoMentors[0];
    const draft = buildEvidenceGroundedDraft({
      mentor,
      papers: [mentor.papers[0]],
      profile: demoProfile,
      now: () => new Date("2026-07-31T09:00:00.000Z"),
    });

    expect(draft.mode).toBe("deterministic-demo");
    expect(draft.generatedAt).toBe("2026-07-31T09:00:00.000Z");
    expect(draft.body).toContain(demoProfile.name);
    expect(draft.body).toContain(mentor.papers[0].title);
    expect(draft.body).not.toContain(mentor.papers[1].title);
    expect(draft.evidenceLinks).toEqual([
      mentor.sourceUrl,
      mentor.papers[0].sourceUrl,
    ]);
  });

  it("does not turn title-only metadata into a technical claim", () => {
    const mentor = demoMentors[0];
    const paper = mentor.papers[1];
    const draft = buildEvidenceGroundedDraft({
      mentor,
      papers: [paper],
      profile: demoProfile,
    });

    expect(draft.body).toContain("only title-level metadata is available");
    expect(draft.body).not.toContain(paper.summary);
  });
});
