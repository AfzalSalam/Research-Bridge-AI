import type { MentorCandidateResult } from "@/features/discovery/contracts";
import { Button } from "@/components/ui/button";
import { EvidenceLink } from "@/features/demo/components/evidence-link";

export function groupAuthorsByPaper(candidates: MentorCandidateResult[]) {
  const groups = new Map<string, { paper: MentorCandidateResult["supportingPapers"][number]; authors: MentorCandidateResult[] }>();
  for (const author of candidates) for (const paper of author.supportingPapers) {
    const group = groups.get(paper.id) ?? { paper, authors: [] };
    if (!group.authors.some((item) => item.id === author.id)) group.authors.push(author);
    groups.set(paper.id, group);
  }
  return [...groups.values()].sort((a, b) => b.authors.length - a.authors.length || b.paper.publicationYear - a.paper.publicationYear);
}

export function PaperAuthorGroups({ candidates, onSelect }: { candidates: MentorCandidateResult[]; onSelect: (id: string) => void }) {
  const groups = groupAuthorsByPaper(candidates);
  return <section aria-labelledby="paper-authors-heading" className="mb-8 space-y-4">
    <h2 id="paper-authors-heading" className="text-2xl font-medium">Find people through a paper</h2>
    <p className="text-sm text-muted-foreground">People listed below share a paper in these results. This may be only part of the author list. Their professor status and internship availability are not confirmed.</p>
    {groups.map(({ paper, authors }) => <details key={paper.id} className="rounded-lg border border-border p-4">
      <summary className="cursor-pointer font-medium">{paper.title} · {authors.length} {authors.length === 1 ? "author" : "authors"} in results</summary>
      <div className="mt-4"><EvidenceLink href={paper.sourceUrl}>View paper and full author record</EvidenceLink></div>
      <ul className="mt-3 divide-y divide-border">{authors.map((author) => {
        const evidence = author.supportingPapers.find((item) => item.id === paper.id)!;
        return <li key={author.id} className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div><p className="font-medium">{author.displayName}</p><p className="text-sm text-muted-foreground">{evidence.authorship.affiliationsAtPublication.map((item) => item.displayName).join(" · ") || "Affiliation not provided"} (at publication)</p>{evidence.authorship.isCorresponding && <p className="text-xs text-brand-teal-strong">Corresponding author on this paper</p>}</div>
          <Button variant="outline" onClick={() => onSelect(author.id)}>Review {author.displayName}</Button>
        </li>;
      })}</ul>
    </details>)}
  </section>;
}
