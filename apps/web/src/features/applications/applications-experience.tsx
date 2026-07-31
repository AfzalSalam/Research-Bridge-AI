"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Clock3, Save, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { DataState } from "@/components/states/data-state";
import { StatusBadge } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EvidenceLink } from "@/features/demo/components/evidence-link";
import { NativeSelect } from "@/features/demo/components/native-select";
import {
  applicationStatusSchema,
  type Application,
} from "@/features/demo/contracts";
import { useDemoStore } from "@/features/demo/demo-store";

const trackerFormSchema = z.object({
  status: applicationStatusSchema,
  notes: z.string().trim().max(1000, "Keep notes below 1,000 characters."),
  followUpDate: z.string(),
});

type TrackerFormValues = z.infer<typeof trackerFormSchema>;

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function TrackerCard({ application }: { application: Application }) {
  const { dispatch } = useDemoStore();
  const [announcement, setAnnouncement] = useState("");
  const {
    formState: { errors, isDirty },
    handleSubmit,
    register,
    reset,
  } = useForm<TrackerFormValues>({
    defaultValues: {
      status: application.status,
      notes: application.notes,
      followUpDate: application.followUpDate ?? "",
    },
    resolver: zodResolver(trackerFormSchema),
  });

  useEffect(() => {
    reset({
      status: application.status,
      notes: application.notes,
      followUpDate: application.followUpDate ?? "",
    });
  }, [application, reset]);

  function updateApplication(values: TrackerFormValues) {
    dispatch({
      type: "update-application",
      applicationId: application.id,
      status: values.status,
      notes: values.notes,
      followUpDate: values.followUpDate || null,
      changedAt: new Date().toISOString(),
    });
    setAnnouncement("Application record updated in this browser session.");
  }

  return (
    <article className="border border-border bg-surface p-5 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone="evidence">{application.status}</StatusBadge>
            <StatusBadge>{application.targetType}</StatusBadge>
          </div>
          <h2 className="mt-4 text-2xl font-medium">{application.targetLabel}</h2>
          <EvidenceLink className="mt-3" href={application.sourceUrl}>Review source evidence</EvidenceLink>
        </div>
        <p className="text-xs leading-5 text-muted-foreground">
          Updated {formatDateTime(application.updatedAt)}
        </p>
      </div>

      <form className="mt-6 grid gap-5" noValidate onSubmit={handleSubmit(updateApplication)}>
        <div className="grid gap-5 sm:grid-cols-2">
          <Field data-invalid={Boolean(errors.status)}>
            <FieldLabel htmlFor={`${application.id}-status`}>Status</FieldLabel>
            <NativeSelect
              aria-invalid={Boolean(errors.status)}
              id={`${application.id}-status`}
              {...register("status")}
            >
              <option>Saved</option>
              <option>Drafting</option>
              <option>Ready for review</option>
              <option>Applied</option>
              <option>Interviewing</option>
              <option>Closed</option>
            </NativeSelect>
            <FieldError errors={[errors.status]} />
          </Field>
          <Field data-invalid={Boolean(errors.followUpDate)}>
            <FieldLabel htmlFor={`${application.id}-follow-up`}>Follow-up date</FieldLabel>
            <Input
              aria-invalid={Boolean(errors.followUpDate)}
              id={`${application.id}-follow-up`}
              type="date"
              {...register("followUpDate")}
            />
            <FieldError errors={[errors.followUpDate]} />
          </Field>
        </div>
        <Field data-invalid={Boolean(errors.notes)}>
          <FieldLabel htmlFor={`${application.id}-notes`}>Private demo notes</FieldLabel>
          <Textarea
            aria-invalid={Boolean(errors.notes)}
            id={`${application.id}-notes`}
            rows={4}
            {...register("notes")}
          />
          <FieldError errors={[errors.notes]} />
        </Field>
        <div className="flex flex-wrap items-center gap-4">
          <Button type="submit" variant="evidence">
            <Save aria-hidden="true" />
            Save tracker update
          </Button>
          <p aria-live="polite" className="text-sm text-muted-foreground">
            {announcement || (isDirty ? "Unsaved tracker changes" : "Record is up to date")}
          </p>
        </div>
      </form>

      <details className="mt-6 border-t border-border pt-5">
        <summary className="cursor-pointer text-sm font-bold text-foreground">
          Status history ({application.history.length})
        </summary>
        <ol className="mt-4 space-y-3">
          {[...application.history].reverse().map((event, index) => (
            <li className="grid grid-cols-[1rem_minmax(0,1fr)] gap-3 text-sm" key={`${event.changedAt}-${index}`}>
              <Clock3 aria-hidden="true" className="mt-0.5 size-4 text-brand-indigo" />
              <span>
                <span className="font-semibold text-foreground">{event.status}</span>
                <span className="block text-xs leading-5 text-muted-foreground">{formatDateTime(event.changedAt)}</span>
              </span>
            </li>
          ))}
        </ol>
      </details>
    </article>
  );
}

export function ApplicationsExperience() {
  const { hydrated, state } = useDemoStore();

  if (!hydrated) {
    return (
      <DataState
        description="Restoring validated fictional application records from this browser session."
        kind="loading"
        title="Loading the application tracker"
      />
    );
  }

  if (state.applications.length === 0) {
    return (
      <DataState
        action={
          <div className="flex flex-wrap gap-3">
            <Button asChild variant="evidence">
              <Link href="/mentors">Prepare outreach <ArrowRight aria-hidden="true" /></Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/opportunities">Browse opportunities</Link>
            </Button>
          </div>
        }
        description="Create a paper-grounded mentor draft or save an opportunity, then explicitly add it here. The demo does not imply that an application was submitted."
        kind="empty"
        title="No applications are being tracked"
      />
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
      <section className="grid gap-5" aria-label="Tracked applications">
        {state.applications.map((application) => (
          <TrackerCard application={application} key={application.id} />
        ))}
      </section>
      <aside className="border border-brand-teal/20 bg-brand-teal-soft/55 p-6 lg:sticky lg:top-24">
        <ShieldCheck aria-hidden="true" className="size-6 text-brand-teal" />
        <h2 className="mt-5 text-xl font-medium">State means what it says</h2>
        <ul className="mt-4 space-y-3 text-sm leading-6 text-muted-foreground">
          <li>“Ready for review” is not “Applied.”</li>
          <li>Status changes happen only when you save them.</li>
          <li>No email or university system is connected.</li>
          <li>Resetting the demo clears the session tracker.</li>
        </ul>
      </aside>
    </div>
  );
}
