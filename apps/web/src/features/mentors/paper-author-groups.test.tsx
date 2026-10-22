import { expect, it } from "vitest";
import { groupAuthorsByPaper } from "./paper-author-groups";
import { completeMentorResponse } from "@/test/fixtures/mentor-response";

it("groups only stable shared paper IDs and deduplicates repeated authors", () => {
  const first = completeMentorResponse.candidates[0];
  const second = { ...first, id: "second-author", displayName: "Another Author" };
  const groups = groupAuthorsByPaper([first, second, first]);
  expect(groups[0].authors.map((author) => author.id)).toEqual([first.id, second.id]);
  const unrelated = { ...second, supportingPapers: [{ ...first.supportingPapers[0], id: "different-paper" }] };
  expect(groupAuthorsByPaper([first, unrelated]).every((group) => group.authors.length === 1)).toBe(true);
});
