"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getLiveOutreachDraft } from "@/lib/api/outreach";
import { DraftEditor } from "@/features/outreach/live-outreach-workspace";
export function RestoredDraft({draftId}:{draftId:string}){
 const cache=useQueryClient();const draft=useQuery({queryKey:["draft",draftId],queryFn:()=>getLiveOutreachDraft({draftId})});
 if(draft.isPending)return <p role="status">Loading saved draft…</p>;
 if(draft.error)return <p role="alert">{draft.error.message}</p>;
 return <DraftEditor key={draft.data.id} draft={draft.data} onDraftChange={d=>cache.setQueryData(["draft",draftId],d)}/>;
}
