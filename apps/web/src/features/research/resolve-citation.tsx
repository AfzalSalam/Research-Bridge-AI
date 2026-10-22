"use client";
import Link from "next/link";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { discoverOpenAlexPapers } from "@/lib/api/discovery";
import { useResearchTask } from "@/features/discovery/research-session";
import { paperDiscoveryResponseSchema } from "@/features/discovery/contracts";
import { citationIdentifier, normalizeCitationDoi } from "./citation-identifier";

export function ResolveCitation({ doi, publicationUrl }: { doi: string | null; publicationUrl?: string }) {
  const identifier = citationIdentifier(doi, publicationUrl);
  const resolve = useResearchTask(`citation-${identifier?.doi ?? publicationUrl ?? "unknown"}`, paperDiscoveryResponseSchema, z.object({ query: z.string() }),
    ({ query }, signal) => discoverOpenAlexPapers({ query, limit: 10, signal }));
  if (!identifier) return <p className="text-xs text-muted-foreground">Author identity is unresolved. Review the publication source before outreach.</p>;
  const match = resolve.data?.papers.find(p => normalizeCitationDoi(p.doi) === identifier.doi);
  return <div className="space-y-2">
    <Button variant="outline" disabled={resolve.isPending} onClick={() => resolve.mutate({ query: identifier.doi })}>{resolve.isPending ? "Checking the paper identifier…" : "Resolve paper and authors"}</Button>
    {identifier.arxiv && <p className="text-xs text-muted-foreground">Matches the canonical arXiv paper, not a particular revision. The original citation remains available above.</p>}
    {match && <Link className="ml-3 underline" href={`/research/papers/${match.id}`}>Read, save, and contact authors</Link>}
    {resolve.status === "success" && !match && <p role="status">No exact identifier match found in the catalog. Author identity remains unresolved.</p>}
    {resolve.status === "interrupted" && <p role="status">Resolution interrupted by refresh. Try again to finish checking.</p>}
    {resolve.error && <p role="alert">{resolve.error}</p>}
  </div>;
}
