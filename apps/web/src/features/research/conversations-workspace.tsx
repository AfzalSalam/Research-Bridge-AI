"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listDrafts } from "@/lib/api/research";
export function ConversationsWorkspace(){
 const drafts=useQuery({queryKey:["outreach-drafts"],queryFn:listDrafts});
 return <section className="space-y-5"><p>Continue your saved outreach with its original paper and researcher.</p>{drafts.isPending && <p role="status">Loading drafts…</p>}{drafts.error && <p role="alert">{drafts.error.message}</p>}{drafts.data?.length===0 && <p>No conversations started. <Link className="underline" href="/discover">Find a paper and choose an author</Link>.</p>}<ul className="divide-y divide-border">{drafts.data?.map(d=><li className="space-y-2 py-5" key={d.id}><h2 className="text-xl">{d.recipientDisplayName}</h2><p>{d.subject}</p><p className="text-sm text-muted-foreground">Draft · version {d.draftVersion} · {d.recipientContact ?? "Choose a recipient address"}</p><Link className="underline" href={`/conversations/drafts/${d.id}`}>Continue draft</Link></li>)}</ul><Link className="underline" href="/applications">View existing application records</Link></section>;
}
