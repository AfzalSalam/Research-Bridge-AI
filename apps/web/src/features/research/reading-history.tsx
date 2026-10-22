"use client";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { readReadingHistory } from "@/lib/api/documents";

export function ReadingHistory({id, onPage}:{id:string;onPage:(page:number)=>void}) {
 const history = useQuery({queryKey:["reading-history",id],queryFn:()=>readReadingHistory(id),retry:false});
 return <section aria-label="Saved reading questions" className="space-y-3 border-t border-border pt-4">
  <h3 className="font-medium">Saved reading questions</h3>
  <p className="text-sm">Your latest 20 completed questions for this PDF, newest first. Saved privately to your account and removed when you delete the PDF. Previous questions are not sent to the AI.</p>
  {history.isPending && <p role="status">Loading saved questions...</p>}
  {history.error && <div role="alert">Could not load saved questions. <Button variant="outline" onClick={()=>history.refetch()}>Retry history</Button></div>}
  {history.data?.length === 0 && <p>No saved questions yet.</p>}
  {history.data?.map(entry=><details key={entry.id} className="rounded border border-border p-3">
   <summary className="cursor-pointer break-words">{entry.question}</summary>
   <p className="text-sm">{new Date(entry.created_at).toLocaleString()} · {entry.model}</p>
   {entry.result.status !== "answer" && <p>{entry.result.status === "unavailable" ? "An answer could not be completed or verified." : "The retrieved text did not provide enough supported evidence."}</p>}
   {entry.result.claims.map((claim,index)=><div key={index} className="space-y-2 py-2"><p className="break-words">{claim.text}</p>{claim.citations.map((citation,n)=><div key={n}><blockquote className="whitespace-pre-wrap break-words text-sm">{citation.quote}</blockquote><Button variant="outline" onClick={()=>onPage(citation.page)}>Read saved cited page {citation.page}</Button></div>)}</div>)}
   <p className="text-sm text-muted-foreground">{entry.result.notice} AI checks can miss mistakes; verify the source.</p>
  </details>)}
 </section>;
}
