"use client";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { listResearch, saveResearch, type ResearchItem } from "@/lib/api/research";
const noteSchema=z.object({collection:z.string().trim().min(1).max(120),note:z.string().max(5000),authorIds:z.array(z.string())});
function SavedPaper({item}:{item:ResearchItem}) {
 const cache=useQueryClient();
 const {register,handleSubmit}=useForm({defaultValues:{collection:item.collection,note:item.note,authorIds:item.authorIds},resolver:zodResolver(noteSchema)});
 const save=useMutation({mutationFn:(values:z.infer<typeof noteSchema>)=>saveResearch(item.paper.id,values),onSuccess:()=>cache.invalidateQueries({queryKey:["research-library"]})});
 return <article className="space-y-4 border-b border-border py-6"><h2 className="text-xl font-medium">{item.paper.title}</h2><p className="text-sm">{item.paper.publicationYear} · {item.paper.venue ?? "Venue unknown"}</p>
 <Link className="underline" href={`/research/papers/${item.paper.id}`}>Read paper and choose an author</Link>
 <form className="space-y-3" onSubmit={handleSubmit(v=>save.mutate(v))}><label className="block">Collection<input className="mt-1 block w-full rounded border border-border p-2" {...register("collection")}/></label><label className="block">Your reading notes<textarea className="mt-1 block min-h-24 w-full rounded border border-border p-2" {...register("note")}/></label>
 <fieldset><legend>Shortlist authors of this paper</legend>{item.paper.authors.map(a=><label className="mr-4 inline-flex gap-2" key={a.id}><input type="checkbox" value={a.id} {...register("authorIds")}/>{a.displayName}</label>)}</fieldset>
 <Button disabled={save.isPending}>Save notes and shortlist</Button>{save.isSuccess && <p role="status">Saved to your account.</p>}{save.error && <p role="alert">{save.error.message}</p>}</form></article>;
}
export function ResearchWorkspace(){
 const query=useQuery({queryKey:["research-library"],queryFn:listResearch});
 return <div className="space-y-5"><p>Keep papers, notes, and shortlisted researchers together across devices.</p>{query.isPending && <p role="status">Loading your research…</p>}{query.error && <p role="alert">{query.error.message}</p>}{query.data?.length===0 && <p>No saved papers yet. <Link href="/discover" className="underline">Discover your first paper</Link>.</p>}{query.data?.map(item=><SavedPaper key={item.id} item={item}/>)}</div>;
}
