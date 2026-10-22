"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EvidenceLink } from "@/features/demo/components/evidence-link";
import { useResearchTask, useResearchValue } from "@/features/discovery/research-session";
import { findPublicEmail } from "@/lib/api/contact";
import { contactRequestSchema, contactResponseSchema } from "./contact-contracts";

const formSchema = z.object({ profileUrl: z.union([z.literal(""), z.string().url("Enter a complete official HTTPS profile URL.").max(1800)]) });
const messages = {
  found: "Public email found on a matching official profile",
  "not-found": "No attributable public email found in the pages checked",
  "needs-review": "Possible profile found — email attribution needs review",
  unsupported: "An official institution website could not be verified from the available metadata",
  blocked: "The official pages could not be checked",
};

export function PublicEmailLookup({ authorId, authorName }: { authorId: string; authorName: string }) {
  const [, setSelectedEmail] = useResearchValue(`selected-email-${authorId}`, z.string(), "");
  const task = useResearchTask(`public-email-${authorId}`, contactResponseSchema, contactRequestSchema,
    (values, signal) => findPublicEmail(authorId, values, signal));
  const [savedForm, setSavedForm] = useResearchValue(`public-email-form-${authorId}`, z.object({ profileUrl: z.string() }), { profileUrl: "" });
  const { register, handleSubmit, subscribe, formState: { errors } } = useForm({ defaultValues: savedForm, resolver: zodResolver(formSchema) });
  useEffect(() => subscribe({ formState: { values: true }, callback: ({ values }) => setSavedForm(values) }), [subscribe, setSavedForm]);
  const [now, setNow] = useState(() => Date.now());
  const [copyStatus, setCopyStatus] = useState("");
  useEffect(() => { if (!task.isPending) return; const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, [task.isPending]);
  const elapsed = Math.max(0, Math.floor((now - (task.startedAt ?? now)) / 1000));
  const result = task.data;
  async function copy(email: string) {
    try { await navigator.clipboard.writeText(email); setCopyStatus("Email copied. Review the source before contacting this person."); }
    catch { setCopyStatus("Clipboard unavailable. Select and copy the displayed email manually."); }
  }
  return <section aria-labelledby={`public-email-heading-${authorId}`} className="mt-7 space-y-4 rounded-lg border border-border bg-surface p-5">
    <h3 id={`public-email-heading-${authorId}`} className="text-xl font-semibold">Find a public email</h3>
    <p className="text-sm text-muted-foreground">Look for {authorName}’s email on official university pages and check it against their paper or ORCID evidence. No addresses are guessed and no emails are sent.</p>
    <form onSubmit={handleSubmit(({ profileUrl }) => { setCopyStatus(""); task.mutate({ profileUrl: profileUrl.trim() || undefined }); })} className="space-y-3">
      <details><summary className="cursor-pointer text-sm font-medium">Already found their official profile?</summary>
        <label htmlFor={`profile-url-${authorId}`} className="mt-3 block text-sm">Official profile URL (optional)</label>
        <Input id={`profile-url-${authorId}`} placeholder="https://university.edu/people/name" aria-invalid={!!errors.profileUrl} {...register("profileUrl")} />
        {errors.profileUrl && <p role="alert" className="text-sm text-destructive">{errors.profileUrl.message}</p>}
        <p className="mt-2 text-xs text-muted-foreground">Official domains are verified through institution records worldwide. Use a university or lab profile connected to this researcher’s recorded institutions. Unverified domains are skipped.</p>
      </details>
      <div className="flex flex-wrap gap-3">
        <Button disabled={task.isPending} type="submit">{task.isPending ? "Checking official pages…" : "Find public email"}</Button>
        {task.isPending && <Button type="button" variant="outline" onClick={task.cancel}>Cancel email lookup</Button>}
        {result && !task.isPending && <Button type="button" variant="outline" onClick={() => { setCopyStatus(""); task.mutate({ profileUrl: result.lookupUrl ?? undefined, refresh: true }); }}>Recheck sources</Button>}
      </div>
    </form>
    <div role="status" aria-live="polite" className="text-sm">
      {task.isPending && <p>{elapsed}s elapsed · allow up to 90 seconds. You can switch sections while this lookup continues.</p>}
      {task.status === "interrupted" && <p>The page was refreshed. Restart the unfinished lookup.</p>}
      {task.status === "cancelled" && <p>Lookup cancelled. You can try again.</p>}
      {copyStatus && <p>{copyStatus}</p>}
    </div>
    {task.error && <p role="alert" className="text-sm text-destructive">{task.error}</p>}
    {result && <div className="space-y-4">
      <p className="font-medium">{messages[result.status]}</p>
      <p className="text-xs text-muted-foreground">Checked {new Date(result.checkedAt).toLocaleString()} · {result.pagesChecked} pages · {result.cacheHit ? "Recent saved evidence" : `${result.elapsedSeconds}s lookup`}</p>
      {result.emails.map((item) => <div key={item.email} className="space-y-2 border-t border-border pt-3">
        <p className="break-all font-semibold select-all">{item.email}</p>
        <Button variant="outline" onClick={() => copy(item.email)}>Copy email</Button>
        <Button variant="outline" onClick={() => {setSelectedEmail(item.email);setCopyStatus("Email selected for this researcher’s draft.");}}>Use in outreach draft</Button>
        <div><EvidenceLink href={item.sourceUrl}>View email on official source</EvidenceLink></div>
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">{item.identityEvidence.map((evidence) => <li key={evidence}>{evidence}</li>)}</ul>
      </div>)}
      {result.status !== "found" && result.profiles.map((profile) => <div key={profile.sourceUrl} className="text-sm"><EvidenceLink href={profile.sourceUrl}>Review possible official profile</EvidenceLink><p className="mt-1 text-muted-foreground">{profile.reason}</p></div>)}
      {(result.institutionSources?.length ?? 0) > 0 && <details><summary className="cursor-pointer text-sm">Institution website verification</summary>{result.institutionSources?.map((url) => <div key={url}><EvidenceLink href={url}>View institution registry record</EvidenceLink></div>)}</details>}
      {result.warnings.length > 0 && <details><summary className="cursor-pointer text-sm">Lookup limitations ({result.warnings.length})</summary><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">{result.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></details>}
      <p className="text-xs text-muted-foreground">A source match confirms public publication of the address, not inbox deliverability, professor status or availability. Positive lookups are cached for seven days; use Recheck sources for a fresh check.</p>
    </div>}
  </section>;
}
