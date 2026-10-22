"use client";
import { useQuery } from "@tanstack/react-query";
import { candidateSchema,researchRequest } from "@/lib/api/research";
import { PublicEmailLookup } from "@/features/mentors/public-email-lookup";
import { LiveOutreachWorkspace } from "@/features/outreach/live-outreach-workspace";
export function SelectedAuthor({paperId,authorId}:{paperId:string;authorId:string}) {
 const result=useQuery({queryKey:["paper-author",paperId,authorId],queryFn:()=>researchRequest(`/research/papers/${paperId}/authors/${authorId}`,candidateSchema)});
 if(result.isPending)return <p role="status">Loading selected author and paper…</p>;
 if(result.error)return <p role="alert">{result.error.message}</p>;
 const author=result.data;
 return <div className="space-y-6"><h2 className="text-2xl font-medium">{author.displayName}</h2><p>Selected from: {author.supportingPapers[0].title}</p><p className="text-sm text-muted-foreground">Review identity, current role, and availability on official sources.</p><PublicEmailLookup authorId={author.id} authorName={author.displayName}/><LiveOutreachWorkspace candidate={author} query={author.supportingPapers[0].title.slice(0,300)}/></div>;
}
