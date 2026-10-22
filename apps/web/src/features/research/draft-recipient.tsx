"use client";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useResearchValue } from "@/features/discovery/research-session";
import { researchRequest } from "@/lib/api/research";
import { getLiveOutreachDraft } from "@/lib/api/outreach";
import type { OutreachDraftResponse } from "@/features/outreach/contracts";
const schema=z.object({email:z.string().email(),manuallyConfirmed:z.boolean()});
export function DraftRecipient({draft,onChange}:{draft:OutreachDraftResponse;onChange:(d:OutreachDraftResponse)=>void}){
 const [selected]=useResearchValue(`selected-email-${draft.mentorId}`,z.string(),"");
 const {register,handleSubmit,setValue,formState:{errors}}=useForm({resolver:zodResolver(schema),defaultValues:{email:draft.recipientContact ?? selected,manuallyConfirmed:false}});
 useEffect(()=>{if(selected)setValue("email",selected);},[selected,setValue]);
 const save=useMutation({mutationFn:async(values:z.infer<typeof schema>)=>{await researchRequest(`/research/drafts/${draft.id}/recipient`,z.null(),{method:"PUT",body:JSON.stringify({...values,expectedVersion:draft.draftVersion})});return getLiveOutreachDraft({draftId:draft.id});},onSuccess:onChange});
 return <section className="mb-6 space-y-3 rounded border border-border p-4"><h3 className="font-medium">Recipient for this draft</h3><form onSubmit={handleSubmit(v=>save.mutate(v))} className="space-y-3"><label className="block">Email address<input className="mt-1 block w-full rounded border border-border p-2" type="email" {...register("email")}/></label>{errors.email && <p role="alert">Enter a valid email.</p>}<label className="flex gap-2 text-sm"><input type="checkbox" {...register("manuallyConfirmed")}/>If not matched by the official lookup, I confirm this address is provided by me and is not verified by the app.</label><Button disabled={save.isPending}>Save recipient</Button>{save.error && <p role="alert">{save.error.message}</p>}</form>{draft.recipientContact && <p className="text-sm">Saved: {draft.recipientContact} · {draft.contactProvenance?.kind === "official-profile" ? "Official-profile evidence" : "Provided by you; not verified by the app"}</p>}</section>;
}
