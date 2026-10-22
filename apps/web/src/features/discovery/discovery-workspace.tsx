"use client";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { UniversityDiscovery } from "./university-discovery";
import { LivePaperDiscovery } from "./live-paper-discovery";
import { useResearchValue } from "./research-session";
import { WorkflowPanel } from "@/features/workflow/workflow-panel";

export function DiscoveryWorkspace() {
  const [source, setSource] = useResearchValue("discovery-source", z.enum(["websites", "papers"]), "papers");
  return <div className="space-y-8">
    <p className="text-sm text-muted-foreground">1. Find papers → 2. Review their authors in Find Professors → 3. Prepare an email. Your results stay when you switch sections.</p>
    <div className="flex flex-wrap gap-3" role="group" aria-label="Where to search">
      <Button aria-pressed={source === "websites"} variant={source === "websites" ? "default" : "outline"} onClick={() => setSource("websites")}>University websites</Button>
      <Button aria-pressed={source === "papers"} variant={source === "papers" ? "default" : "outline"} onClick={() => setSource("papers")}>Academic databases</Button>
    </div>
    {source === "websites" ? <UniversityDiscovery /> : <LivePaperDiscovery />}
    <details className="border-t border-border pt-6"><summary className="cursor-pointer text-lg font-medium">Want help going from a topic to an email?</summary><p className="my-4 text-sm text-muted-foreground">Use the guided journey to find people, choose 1–2 papers, and prepare an email draft. Nothing is sent automatically.</p><WorkflowPanel /></details>
    <p className="text-xs text-muted-foreground">Results are kept for this account in this browser tab. Refresh restores received results, but interrupts unfinished searches. Use Clear results to remove a search.</p>
  </div>;
}
