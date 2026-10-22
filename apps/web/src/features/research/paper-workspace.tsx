"use client";
import Link from "next/link";
import { PaperDocuments } from "./paper-documents";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { researchRequest,paperSchema,saveResearch } from "@/lib/api/research";
import { Button } from "@/components/ui/button";
export function PaperWorkspace({paperId}:{paperId:string}) {
 const cache=useQueryClient(); const paper=useQuery({queryKey:["catalog-paper",paperId],queryFn:()=>researchRequest(`/research/papers/${paperId}`,paperSchema)});
 const save=useMutation({mutationFn:()=>saveResearch(paperId,{}),onSuccess:()=>cache.invalidateQueries({queryKey:["research-library"]})});
 if(paper.isPending)return <p role="status">Loading paper…</p>;
 if(paper.error)return <p role="alert">{paper.error.message}</p>;
 const p=paper.data;
 return <div className="space-y-6"><h1 className="text-3xl font-medium">{p.title}</h1><p>{p.publicationYear} · {p.venue ?? "Venue unknown"}</p><a href={p.sourceUrl} target="_blank" rel="noreferrer" className="underline">Original paper record</a><div><Button disabled={save.isPending || save.isSuccess} onClick={()=>save.mutate()}>{save.isSuccess?"Saved to My Research":"Save to My Research"}</Button>{save.error && <p role="alert">{save.error.message}</p>}</div><section className="space-y-3"><h2 className="text-xl">Available abstract</h2><p className="leading-7">{p.abstractExcerpt ?? "Only title metadata is available. No claims about methods or results are inferred."}</p></section><PaperDocuments key={paperId} paperId={paperId}/><section><h2 className="text-xl">People who wrote this paper</h2><p className="my-2 text-sm text-muted-foreground">Author status does not confirm a professor role or an internship opening.</p><ul className="divide-y divide-border">{p.authors.map(a=><li key={a.id} className="space-y-2 py-4"><h3 className="font-medium">{a.displayName}{a.isCorresponding?" · Corresponding author":""}</h3><p>{a.institutions.map(i=>i.displayName).join("; ") || "Affiliation unknown"}</p><Link className="underline" href={`/mentors?paper=${p.id}&author=${a.id}`}>Find contact and prepare outreach</Link></li>)}</ul></section></div>;
}
