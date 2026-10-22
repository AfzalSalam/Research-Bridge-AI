"use client";
import { ResolveCitation } from "@/features/research/resolve-citation";



import { zodResolver } from "@hookform/resolvers/zod";

import { z } from "zod";

import { useResearchTask, useResearchValue } from "./research-session";

import { useEffect, useState } from "react";

import { useForm } from "react-hook-form";



import { Button } from "@/components/ui/button";

import { Input } from "@/components/ui/input";

import { NativeSelect } from "@/features/demo/components/native-select";

import { scanUniversityWebsites } from "@/lib/api/university";

import {

  universityFormSchema, scanSnapshotSchema, workModeLabels,

  type UniversityForm,

} from "@/features/discovery/university-contracts";



function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {

  return <a className="text-brand-teal-strong underline underline-offset-4 break-words" href={href} target="_blank" rel="noopener noreferrer">{children}<span className="sr-only"> (opens in a new tab)</span></a>;

}



const persistedFormSchema = universityFormSchema.extend({ query: z.string().max(300) });



export function UniversityDiscovery() {

  const [savedForm, setSavedForm] = useResearchValue("university-form", persistedFormSchema, { query: "machine learning", target: "20", region: "both" });

  const [mode, setMode] = useResearchValue("university-mode", z.string(), "all");

  const { register, handleSubmit, subscribe, reset, formState: { errors } } = useForm<UniversityForm>({

    resolver: zodResolver(universityFormSchema), defaultValues: savedForm,

  });

  useEffect(() => subscribe({ formState: { values: true }, callback: ({ values }) => { const parsed = persistedFormSchema.safeParse(values); if (parsed.success) setSavedForm(parsed.data); } }), [subscribe, setSavedForm]);

  const scan = useResearchTask("university-scan", scanSnapshotSchema, universityFormSchema, scanUniversityWebsites);

  const snapshot = scan.data;

  const cancelled = scan.status === "cancelled";

  const [now, setNow] = useState(() => Date.now());

  useEffect(() => { if (!scan.isPending) return; const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, [scan.isPending]);

  const elapsed = scan.isPending && scan.startedAt ? Math.max(snapshot?.elapsedSeconds ?? 0, Math.floor((now - scan.startedAt) / 1000)) : snapshot?.elapsedSeconds ?? 0;

  const programs = snapshot?.programs.filter((program) => mode === "all" || program.workMode === mode) ?? [];

  const active = scan.isPending && !cancelled;

  return (

    <section aria-labelledby="university-scan-heading" className="space-y-6">

      <div>

        <h2 id="university-scan-heading" className="text-xl font-semibold">Search university websites</h2>

        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">Find papers and internship details on official university websites worldwide. Choose how many papers you want; we select the sources. Allow up to 2 minutes. You can browse other sections while the scan continues.</p>

      </div>

      <form onSubmit={handleSubmit((form) => scan.mutate(form))} className="space-y-5">

        <div className="grid gap-4 sm:grid-cols-[1fr_10rem]">

          <div>

            <label htmlFor="university-topic" className="mb-2 block text-sm font-medium">What topic interests you?</label>

            <Input id="university-topic" {...register("query")} aria-invalid={!!errors.query} aria-describedby={errors.query ? "university-topic-error" : undefined} />

            {errors.query && <p id="university-topic-error" role="alert" className="mt-2 text-sm text-destructive">{errors.query.message}</p>}

          </div>

          <div>

            <label htmlFor="university-target" className="mb-2 block text-sm font-medium">Number of papers</label>

            <NativeSelect id="university-target" {...register("target")}>

              {[10, 20, 30].map((n) => <option value={String(n)} key={n}>{n} papers</option>)}

            </NativeSelect>

          </div>

        </div>

        <div className="max-w-xs"><label htmlFor="university-region" className="mb-2 block text-sm font-medium">Where would you like to research?</label><NativeSelect id="university-region" disabled={active} {...register("region")}><option value="both">India and international</option><option value="india">India</option><option value="international">International</option></NativeSelect></div>

        <details className="text-sm text-muted-foreground"><summary className="cursor-pointer">Which universities are included?</summary><p className="mt-2">We discover relevant institutions worldwide from papers on your topic, verify their official websites through ROR, and scan up to six newly identified institutions alongside reviewed starting sources. Your location choice narrows the search. Coverage varies with available metadata and website access; no scan covers every university.</p></details>

        <div className="flex flex-wrap gap-3">

          <Button type="submit" disabled={scan.isPending}>{active ? "Scanning university websites…" : "Scan university websites"}</Button>

          {active && <Button type="button" variant="outline" onClick={scan.cancel}>Cancel scan</Button>}

          {!active && snapshot && <Button type="button" variant="outline" onClick={() => { scan.clear(); reset({ query: "", target: "20", region: savedForm.region }); document.getElementById("university-topic")?.focus(); }}>New search</Button>}

          {!active && snapshot && <Button type="button" variant="outline" onClick={scan.clear}>Clear results</Button>}

        </div>

      </form>

      <p className="text-xs leading-5 text-muted-foreground">Only registry-verified or reviewed university domains are visited. Pages may be skipped because of access rules. Matches use publication text, not an AI relevance score. No emails are sent.</p>

      <div aria-live="polite" role="status" className="text-sm">

        {cancelled ? "Scan cancelled. Results already found remain below." : active ? `Scanning ${snapshot?.currentUniversity ?? "reviewed sources"} · ${snapshot?.pagesRead ?? 0} pages read · ${elapsed}s elapsed · up to 2 minutes total` : null}

        {snapshot && <p className="mt-2 font-medium">Found {snapshot.papers.length} of {snapshot.target} requested papers</p>}

      </div>

      {scan.status === "interrupted" && <p role="status" className="text-sm text-muted-foreground">The page was refreshed before the scan finished. Your received results are restored; start another scan to continue searching.</p>}

      {scan.isError && <p role="alert" className="rounded-lg border border-destructive p-4 text-sm">{scan.error}</p>}

      {snapshot && <>

        {(snapshot.sources?.length ?? 0) > 0 && <details className="text-sm"><summary className="cursor-pointer font-medium">Universities selected for this scan ({snapshot.sources.length})</summary><p className="mt-2 text-muted-foreground">The time budget may prevent checking every selected website.</p><ul className="mt-3 space-y-2">{snapshot.sources.map((source) => <li key={source.website}><SourceLink href={source.website}>{source.name}</SourceLink>{source.registryUrl && <> · <SourceLink href={source.registryUrl}>Institution record</SourceLink></>}</li>)}</ul></details>}

        {!active && snapshot.papers.length < snapshot.target && <p className="text-sm text-muted-foreground">The scan did not reach your target. Try a more specific topic or a different region; unrelated papers are never added to fill the list.</p>}

        {snapshot.warnings.length > 0 && <details className="text-sm"><summary className="cursor-pointer font-medium">Source limitations ({snapshot.warnings.length})</summary><ul className="mt-3 list-disc space-y-2 pl-5">{snapshot.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></details>}

        <section aria-labelledby="university-papers-heading">

          <h3 id="university-papers-heading" className="text-lg font-medium">Papers found ({snapshot.papers.length})</h3>

          {!snapshot.papers.length && !active && <p className="mt-3 text-sm text-muted-foreground">No matching publication citations were extracted from the pages reached.</p>}

          <ol className="mt-3 divide-y divide-border">

            {snapshot.papers.map((paper) => <li key={paper.id} className="space-y-3 py-5">

              <h4 className="font-medium break-words">{paper.title ?? "Publication citation"}</h4>
              <ResolveCitation doi={paper.doi} publicationUrl={paper.publicationUrl} />

              <p className="text-sm leading-6 break-words">{paper.citation}</p>

              <p className="text-xs text-muted-foreground">{paper.university} · Matched: {paper.matchedTerms.join(", ")} · Checked {new Date(paper.checkedAt).toLocaleDateString()}</p>

              <div className="flex flex-wrap gap-5 text-sm"><SourceLink href={paper.sourceUrl}>University evidence</SourceLink><SourceLink href={paper.publicationUrl}>Publication link</SourceLink></div>

            </li>)}

          </ol>

        </section>

        <section aria-labelledby="university-programs-heading" className="space-y-4 border-t border-border pt-6">

          <h3 id="university-programs-heading" className="text-lg font-medium">Internship programs ({snapshot.programs.length})</h3>

          <p className="text-sm text-muted-foreground">Program eligibility is separate from paper relevance. A program does not mean every professor is accepting interns. Indian-student preference is not inferred.</p>

          <div className="max-w-xs"><label htmlFor="university-work-mode" className="mb-2 block text-sm font-medium">Internship work mode</label><NativeSelect id="university-work-mode" value={mode} onChange={(e) => setMode(e.target.value)}><option value="all">All modes</option>{Object.entries(workModeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</NativeSelect></div>

          {!programs.length && <p className="text-sm text-muted-foreground">No verified program evidence matches this work-mode filter.</p>}

          {programs.map((program) => <article key={program.sourceUrl} className="space-y-3 rounded-lg border border-border p-5">

            <h4 className="font-medium">{program.university} — {program.name}</h4>

            <p className="text-sm font-medium">{workModeLabels[program.workMode]} · {program.status === "not-confirmed" ? "Application status not confirmed" : program.status === "rolling" ? "Rolling applications" : program.status === "open" ? "Application deadline ahead" : "Applications closed"}{program.deadline ? ` · Deadline: ${program.deadline}` : ""}</p>

            {program.workModeEvidence ? <blockquote className="border-l-2 border-border pl-3 text-sm">{program.workModeEvidence}</blockquote> : <p className="text-sm text-muted-foreground">Work mode is not explicitly established by the extracted evidence.</p>}

            {program.statusEvidence && <p className="text-sm leading-6">{program.statusEvidence}</p>}

            {program.eligibilityEvidence && <p className="text-sm leading-6">{program.eligibilityEvidence}</p>}

            <p className="text-sm text-muted-foreground">{program.applicationNote}</p>

            <p className="text-xs text-muted-foreground">Checked {new Date(program.checkedAt).toLocaleString()}</p>

            <SourceLink href={program.sourceUrl}>Official program and eligibility</SourceLink>

          </article>)}

        </section>

      </>}

    </section>

  );

}

