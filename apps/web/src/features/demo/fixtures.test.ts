import { describe, expect, it } from "vitest";

import { demoMentors, demoOpportunities } from "@/features/demo/fixtures";

describe("Phase 3 fictional fixtures", () => {
  it("uses visibly fictional identities and inert example.org evidence links", () => {
    expect(demoMentors.every((mentor) => mentor.name.includes("(fictional)"))).toBe(true);

    const urls = [
      ...demoMentors.flatMap((mentor) => [
        mentor.sourceUrl,
        ...mentor.papers.map((paper) => paper.sourceUrl),
      ]),
      ...demoOpportunities.map((opportunity) => opportunity.sourceUrl),
    ];
    expect(urls.every((url) => new URL(url).hostname === "example.org")).toBe(true);
  });

  it("does not introduce ranking fields", () => {
    for (const mentor of demoMentors) {
      expect(mentor).not.toHaveProperty("score");
      expect(mentor).not.toHaveProperty("rank");
      expect(mentor).not.toHaveProperty("responseRate");
    }
  });
});
