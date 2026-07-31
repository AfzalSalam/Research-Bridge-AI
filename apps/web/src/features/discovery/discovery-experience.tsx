"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, FileSearch, Search, SlidersHorizontal } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { DataState } from "@/components/states/data-state";
import { StatusBadge } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/features/demo/components/native-select";
import { ProgressStages } from "@/features/demo/components/progress-stages";
import { discoveryScenarioSchema } from "@/features/demo/contracts";
import { useDemoStore } from "@/features/demo/demo-store";
import { DEMO_DISCOVERY_QUERY, demoMentors } from "@/features/demo/fixtures";

const discoveryFormSchema = z.object({
  query: z.string().trim().min(12, "Describe a focused topic using at least 12 characters.").max(180),
  scenario: discoveryScenarioSchema,
});

type DiscoveryFormValues = z.infer<typeof discoveryFormSchema>;

const outcomeByScenario = {
  complete: {
    status: "complete" as const,
    mentorIds: demoMentors.map((mentor) => mentor.id),
  },
  partial: {
    status: "partial" as const,
    mentorIds: demoMentors.slice(0, 2).map((mentor) => mentor.id),
  },
  empty: { status: "empty" as const, mentorIds: [] },
  error: { status: "error" as const, mentorIds: [] },
};

function DiscoveryWorkspace() {
  const { dispatch, hydrated, state } = useDemoStore();
  const router = useRouter();
  const timers = useRef<number[]>([]);
  const {
    formState: { errors },
    handleSubmit,
    register,
    reset,
  } = useForm<DiscoveryFormValues>({
    defaultValues: {
      query: state.discovery.query || DEMO_DISCOVERY_QUERY,
      scenario: state.discovery.scenario,
    },
    resolver: zodResolver(discoveryFormSchema),
  });

  useEffect(() => {
    if (!hydrated) return;
    reset({
      query: state.discovery.query || DEMO_DISCOVERY_QUERY,
      scenario: state.discovery.scenario,
    });
  }, [hydrated, reset, state.discovery.query, state.discovery.scenario]);

  useEffect(() => {
    if (state.discovery.status !== "searching") return;

    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current = [];
    timers.current.push(
      window.setTimeout(() => dispatch({ type: "advance-discovery", stage: 1 }), 300),
      window.setTimeout(() => dispatch({ type: "advance-discovery", stage: 2 }), 600),
      window.setTimeout(() => {
        dispatch({ type: "advance-discovery", stage: 3 });
        const outcome = outcomeByScenario[state.discovery.scenario];
        dispatch({
          type: "finish-discovery",
          status: outcome.status,
          mentorIds: outcome.mentorIds,
          errorMessage:
            state.discovery.scenario === "error"
              ? "The fictional OpenAlex adapter timed out. No cached result was substituted."
              : undefined,
        });
      }, 900),
    );

    return () => {
      timers.current.forEach((timer) => window.clearTimeout(timer));
      timers.current = [];
    };
  }, [dispatch, state.discovery.scenario, state.discovery.status]);

  function runDiscovery(values: DiscoveryFormValues) {
    dispatch({ type: "start-discovery", query: values.query, scenario: values.scenario });
  }

  function inspectMentor(mentorId: string) {
    dispatch({ type: "select-mentor", mentorId });
    router.push("/mentors");
  }

  const visibleMentors = state.discovery.mentorIds
    .map((id) => demoMentors.find((mentor) => mentor.id === id))
    .filter((mentor) => mentor !== undefined);

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start">
      <section className="min-w-0">
        <form
          className="border border-border bg-surface p-5 sm:p-7"
          noValidate
          onSubmit={handleSubmit(runDiscovery)}
        >
          <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_13rem_auto] md:items-end">
            <Field data-invalid={Boolean(errors.query)}>
              <FieldLabel htmlFor="discovery-query">Research topic</FieldLabel>
              <Input
                aria-invalid={Boolean(errors.query)}
                id="discovery-query"
                placeholder="e.g. interpretable ML for public health"
                {...register("query")}
              />
              <FieldError errors={[errors.query]} />
            </Field>
            <Field data-invalid={Boolean(errors.scenario)}>
              <FieldLabel htmlFor="scenario">Demo response</FieldLabel>
              <NativeSelect id="scenario" {...register("scenario")}>
                <option value="complete">Complete fixtures</option>
                <option value="partial">Partial source failure</option>
                <option value="empty">No result</option>
                <option value="error">Source error</option>
              </NativeSelect>
              <FieldError errors={[errors.scenario]} />
            </Field>
            <Button disabled={state.discovery.status === "searching"} type="submit" variant="evidence">
              <Search aria-hidden="true" />
              Run demo search
            </Button>
          </div>
          <FieldDescription className="mt-4 border-t border-border pt-4">
            Scenario control is intentionally visible so reviewers can test loading,
            complete, partial, empty, and error states without network tricks.
          </FieldDescription>
        </form>

        <div className="mt-8" aria-live="polite">
          {state.discovery.status === "idle" ? (
            <DataState
              description="Use the prefilled fictional topic or edit it. The query is validated locally before the fixture pipeline runs."
              kind="empty"
              title="Ready for an evidence-led search"
            />
          ) : null}

          {state.discovery.status === "searching" ? (
            <section aria-busy="true" className="border border-border bg-surface p-5 sm:p-7">
              <StatusBadge>Fixture pipeline running</StatusBadge>
              <h2 className="mt-4 text-2xl font-medium">Building a reviewable paper trail</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                This progress is simulated with local records. It demonstrates honest
                workflow states, not real API activity.
              </p>
              <div className="mt-6">
                <ProgressStages activeStage={state.discovery.stage} />
              </div>
            </section>
          ) : null}

          {state.discovery.status === "empty" ? (
            <DataState
              action={
                <Button onClick={() => reset({ query: DEMO_DISCOVERY_QUERY, scenario: "complete" })} variant="outline">
                  Restore example query
                </Button>
              }
              description="The selected scenario returned no fictional records. Broaden the topic or restore the complete fixture set."
              kind="empty"
              title="No paper evidence matched this demo query"
            />
          ) : null}

          {state.discovery.status === "error" ? (
            <DataState
              description={state.discovery.errorMessage ?? "The demo source failed without a replacement result."}
              kind="error"
              title="The source could not be reached"
            />
          ) : null}

          {state.discovery.status === "partial" ? (
            <DataState
              className="mb-6 min-h-0"
              description="One fictional source timed out. Two candidates remain visible with their available evidence; nothing was silently filled in."
              kind="partial"
              title="Two of three fixture records are available"
            />
          ) : null}

          {visibleMentors.length > 0 ? (
            <section aria-labelledby="results-title">
              <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-4">
                <div>
                  <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
                    Demo order · not ranked
                  </p>
                  <h2 className="mt-2 text-3xl font-medium" id="results-title">
                    Researchers connected to paper evidence
                  </h2>
                </div>
                <StatusBadge tone="evidence">{visibleMentors.length} reviewable</StatusBadge>
              </div>
              <div className="divide-y divide-border border-b border-border">
                {visibleMentors.map((mentor, index) => (
                  <article className="grid gap-5 py-7 md:grid-cols-[3rem_minmax(0,1fr)_auto] md:items-start" key={mentor.id}>
                    <span className="grid size-10 place-items-center rounded-full bg-brand-indigo-soft text-sm font-bold text-brand-indigo">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap gap-2">
                        <StatusBadge tone="evidence">{mentor.papers.length} paper sources</StatusBadge>
                        <StatusBadge tone="unknown">Availability unknown</StatusBadge>
                      </div>
                      <h3 className="mt-4 text-2xl font-medium">{mentor.name}</h3>
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">
                        {mentor.role} · {mentor.institution}
                      </p>
                      <p className="mt-4 max-w-2xl text-sm leading-6 text-foreground">
                        {mentor.fitRationale[0]}
                      </p>
                      <ul className="mt-4 flex flex-wrap gap-2" aria-label="Research themes">
                        {mentor.researchThemes.map((theme) => (
                          <li className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground" key={theme}>
                            {theme}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <Button className="md:mt-8" onClick={() => inspectMentor(mentor.id)} variant="outline">
                      Inspect evidence
                      <ArrowRight aria-hidden="true" />
                    </Button>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      </section>

      <aside className="border border-border bg-surface-subtle p-6 lg:sticky lg:top-24">
        <div className="grid size-10 place-items-center rounded-full bg-brand-indigo-soft text-brand-indigo">
          <SlidersHorizontal aria-hidden="true" className="size-5" />
        </div>
        <h2 className="mt-5 text-xl font-medium">What this phase proves</h2>
        <ul className="mt-4 space-y-3 text-sm leading-6 text-muted-foreground">
          <li className="flex gap-2"><FileSearch aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Explicit pipeline stages and typed outcomes.</li>
          <li className="flex gap-2"><FileSearch aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Source failures remain visible to the user.</li>
          <li className="flex gap-2"><FileSearch aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />No score is invented before ranking is evaluated.</li>
        </ul>
      </aside>
    </div>
  );
}

export function DiscoveryExperience() {
  const { hydrated } = useDemoStore();

  if (!hydrated) {
    return (
      <DataState
        description="Restoring the validated fictional discovery state from this browser session."
        kind="loading"
        title="Loading the discovery workspace"
      />
    );
  }

  return <DiscoveryWorkspace />;
}
