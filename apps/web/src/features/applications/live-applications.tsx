"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  Clock3,
  RefreshCw,
  Save,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";

import { DataState } from "@/components/states/data-state";
import { StatusBadge } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  applicationTrackerFormSchema,
  type ApplicationResponse,
  type ApplicationStatus,
  type ApplicationTrackerForm,
} from "@/features/applications/contracts";
import { EvidenceLink } from "@/features/demo/components/evidence-link";
import { NativeSelect } from "@/features/demo/components/native-select";
import {
  listLiveApplications,
  updateLiveApplication,
} from "@/lib/api/applications";
import { ApiError } from "@/lib/api/result";

const statusLabels: Record<ApplicationStatus, string> = {
  saved: "Saved",
  drafting: "Drafting",
  "ready-for-review": "Ready for review",
  applied: "Applied",
  interviewing: "Interviewing",
  closed: "Closed",
};

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function TrackerCard({ application }: { application: ApplicationResponse }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({ mutationFn: updateLiveApplication });
  const {
    formState: { errors, isDirty },
    handleSubmit,
    register,
    reset,
  } = useForm<ApplicationTrackerForm>({
    defaultValues: {
      status: application.status,
      notes: application.notes,
      followUpDate: application.followUpDate ?? "",
    },
    resolver: zodResolver(applicationTrackerFormSchema),
  });

  useEffect(() => {
    reset({
      status: application.status,
      notes: application.notes,
      followUpDate: application.followUpDate ?? "",
    });
  }, [application, reset]);

  const options = useMemo(
    () => [
      application.status,
      ...application.allowedNextStatuses.filter((value) => value !== application.status),
    ],
    [application.allowedNextStatuses, application.status],
  );

  function save(values: ApplicationTrackerForm) {
    mutation.mutate(
      {
        applicationId: application.id,
        expectedVersion: application.version,
        followUpDate: values.followUpDate || null,
        notes: values.notes,
        status: values.status,
      },
      {
        onSuccess: (updated) => {
          queryClient.setQueryData<ApplicationResponse[]>(
            ["applications"],
            (current = []) =>
              current.map((item) => (item.id === updated.id ? updated : item)),
          );
          reset({
            status: updated.status,
            notes: updated.notes,
            followUpDate: updated.followUpDate ?? "",
          });
        },
      },
    );
  }

  const error = mutation.error instanceof ApiError ? mutation.error : null;
  return (
    <article className="overflow-hidden border border-border bg-surface">
      <div className="grid gap-5 border-b border-border bg-[linear-gradient(115deg,var(--brand-indigo-soft),transparent_60%)] p-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:p-7">
        <div className="min-w-0">
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone="evidence">{statusLabels[application.status]}</StatusBadge>
            <StatusBadge>Version {application.version}</StatusBadge>
          </div>
          <h2 className="mt-4 text-2xl font-medium tracking-[-0.02em] text-balance">
            {application.targetLabel}
          </h2>
          <EvidenceLink className="mt-3" href={application.sourceUrl}>
            Review official source
          </EvidenceLink>
        </div>
        <div className="text-sm leading-6 text-muted-foreground sm:text-right">
          <p>Updated {formatDateTime(application.updatedAt)}</p>
          <p className="mt-1 font-semibold text-brand-indigo">
            {application.events.length} recorded event
            {application.events.length === 1 ? "" : "s"}
          </p>
        </div>
      </div>

      <div className="grid gap-7 p-5 sm:p-7 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <form className="grid gap-5" noValidate onSubmit={handleSubmit(save)}>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field data-invalid={Boolean(errors.status)}>
              <FieldLabel htmlFor={`${application.id}-status`}>Recorded status</FieldLabel>
              <NativeSelect
                aria-invalid={Boolean(errors.status)}
                disabled={mutation.isPending}
                id={`${application.id}-status`}
                {...register("status")}
              >
                {options.map((status) => (
                  <option key={status} value={status}>
                    {statusLabels[status]}
                  </option>
                ))}
              </NativeSelect>
              <FieldError errors={[errors.status]} />
            </Field>
            <Field data-invalid={Boolean(errors.followUpDate)}>
              <FieldLabel htmlFor={`${application.id}-follow-up`}>
                Follow-up date
              </FieldLabel>
              <Input
                aria-invalid={Boolean(errors.followUpDate)}
                disabled={mutation.isPending}
                id={`${application.id}-follow-up`}
                type="date"
                {...register("followUpDate")}
              />
              <FieldError errors={[errors.followUpDate]} />
            </Field>
          </div>
          <Field data-invalid={Boolean(errors.notes)}>
            <FieldLabel htmlFor={`${application.id}-notes`}>Private notes</FieldLabel>
            <Textarea
              aria-invalid={Boolean(errors.notes)}
              disabled={mutation.isPending}
              id={`${application.id}-notes`}
              placeholder="Record what you submitted, the contact channel, or the next action."
              rows={5}
              {...register("notes")}
            />
            <FieldError errors={[errors.notes]} />
          </Field>

          {error ? (
            <div className="border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive" role="alert">
              <p>{error.message}</p>
              {error.code === "application_version_conflict" ? (
                <Button
                  className="mt-3"
                  onClick={() => {
                    mutation.reset();
                    void queryClient.invalidateQueries({ queryKey: ["applications"] });
                  }}
                  type="button"
                  variant="outline"
                >
                  <RefreshCw aria-hidden="true" />Reload latest version
                </Button>
              ) : null}
            </div>
          ) : null}

          <div className="flex flex-wrap items-center gap-4">
            <Button disabled={mutation.isPending || !isDirty} type="submit" variant="evidence">
              <Save aria-hidden="true" />
              {mutation.isPending ? "Saving…" : "Save tracker update"}
            </Button>
            <p aria-live="polite" className="text-sm text-muted-foreground">
              {isDirty
                ? "Unsaved changes"
                : mutation.isSuccess
                  ? `Saved as version ${application.version}.`
                  : "Current version loaded"}
            </p>
          </div>
        </form>

        <section className="border-l-2 border-brand-teal pl-5" aria-labelledby={`${application.id}-history`}>
          <div className="flex items-center gap-2">
            <Clock3 aria-hidden="true" className="size-5 text-brand-teal" />
            <h3 className="font-semibold" id={`${application.id}-history`}>
              Immutable history
            </h3>
          </div>
          <ol className="mt-5 space-y-5">
            {[...application.events].reverse().map((event) => (
              <li className="relative pl-5 text-sm" key={event.sequence}>
                <span className="absolute top-1.5 left-0 size-2 rounded-full bg-brand-indigo" />
                <p className="font-semibold text-foreground">
                  {statusLabels[event.toStatus]}
                </p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  {formatDateTime(event.occurredAt)} · Event {event.sequence}
                </p>
                {event.note ? (
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    {event.note}
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        </section>
      </div>
    </article>
  );
}

export function LiveApplications() {
  const query = useQuery({
    queryKey: ["applications"],
    queryFn: ({ signal }) => listLiveApplications({ signal }),
  });
  const error = query.error instanceof ApiError ? query.error : null;
  const appliedCount =
    query.data?.filter((application) =>
      ["applied", "interviewing"].includes(application.status),
    ).length ?? 0;
  const followUpCount =
    query.data?.filter((application) => application.followUpDate !== null).length ?? 0;

  if (query.isPending) {
    return (
      <DataState
        description="Loading owner-scoped application records and their ordered event histories."
        kind="loading"
        title="Loading the durable tracker"
      />
    );
  }

  if (query.isError) {
    return (
      <DataState
        action={
          <Button onClick={() => void query.refetch()} variant="outline">
            <RefreshCw aria-hidden="true" />Retry tracker
          </Button>
        }
        description={`${error?.message ?? "The live tracker could not be loaded."}${error?.requestId ? ` Reference: ${error.requestId}.` : ""}`}
        kind="error"
        title="Application tracker is unavailable"
      />
    );
  }

  if (query.data.length === 0) {
    return (
      <DataState
        action={
          <Button asChild variant="evidence">
            <Link href="/opportunities">
              Find verified opportunities <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
        }
        description="Save a verified opportunity and explicitly choose Track. Research Bridge never marks an external application as submitted for you."
        kind="empty"
        title="No live applications are being tracked"
      />
    );
  }

  return (
    <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_19rem] xl:items-start">
      <section className="grid gap-6" aria-label="Live tracked applications">
        {query.data.map((application) => (
          <TrackerCard application={application} key={application.id} />
        ))}
      </section>
      <aside className="overflow-hidden border border-brand-indigo/20 bg-surface xl:sticky xl:top-24">
        <div className="bg-[linear-gradient(145deg,var(--brand-teal-soft),var(--brand-indigo-soft))] p-6">
          <ShieldCheck aria-hidden="true" className="size-7 text-brand-teal" />
          <h2 className="mt-5 text-xl font-medium">A truthful state machine</h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Every transition is a user record inside this app. No university portal,
            inbox, or email service is connected.
          </p>
        </div>
        <dl className="grid grid-cols-2 gap-px bg-border">
          <div className="bg-surface p-5">
            <dt className="text-xs font-bold text-muted-foreground uppercase">Tracked</dt>
            <dd className="mt-2 text-3xl font-medium">{query.data.length}</dd>
          </div>
          <div className="bg-surface p-5">
            <dt className="text-xs font-bold text-muted-foreground uppercase">Applied</dt>
            <dd className="mt-2 text-3xl font-medium">{appliedCount}</dd>
          </div>
        </dl>
        <div className="p-6">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <CalendarClock aria-hidden="true" className="size-5 text-brand-indigo" />
            {followUpCount} follow-up date{followUpCount === 1 ? "" : "s"}
          </p>
          <p className="mt-4 flex items-center gap-2 text-sm font-semibold">
            <CheckCircle2 aria-hidden="true" className="size-5 text-brand-teal" />
            Optimistic version checks active
          </p>
        </div>
      </aside>
    </div>
  );
}
