"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Save, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { DataState } from "@/components/states/data-state";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { NativeSelect } from "@/features/demo/components/native-select";
import {
  profileFormSchema,
  studentProfileSchema,
  type ProfileFormValues,
  type StudentProfile,
} from "@/features/demo/contracts";
import { useDemoStore } from "@/features/demo/demo-store";

function toFormValues(profile: StudentProfile): ProfileFormValues {
  return {
    name: profile.name,
    program: profile.program,
    institution: profile.institution,
    graduationYear: profile.graduationYear,
    researchInterests: profile.researchInterests.join(", "),
    skills: profile.skills.join(", "),
    projectTitle: profile.projectTitle,
    projectSummary: profile.projectSummary,
    weeklyAvailability: profile.weeklyAvailability,
  };
}

function commaSeparatedValues(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function ProfileForm() {
  const { dispatch, hydrated, state } = useDemoStore();
  const [savedMessage, setSavedMessage] = useState("");
  const {
    formState: { errors, isDirty, isSubmitting },
    handleSubmit,
    register,
    reset,
  } = useForm<ProfileFormValues>({
    defaultValues: toFormValues(state.profile),
    resolver: zodResolver(profileFormSchema),
  });

  useEffect(() => {
    if (hydrated) reset(toFormValues(state.profile));
  }, [hydrated, reset, state.profile]);

  function saveProfile(values: ProfileFormValues) {
    const profile = studentProfileSchema.parse({
      ...values,
      id: "demo-student",
      researchInterests: commaSeparatedValues(values.researchInterests),
      skills: commaSeparatedValues(values.skills),
    });

    dispatch({ type: "save-profile", profile });
    reset(toFormValues(profile));
    setSavedMessage("Fictional profile saved in this browser session.");
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
      <form
        className="border border-border bg-surface p-5 sm:p-8"
        noValidate
        onSubmit={handleSubmit(saveProfile)}
      >
        <div className="border-b border-border pb-6">
          <p className="text-xs font-bold tracking-[0.14em] text-brand-teal uppercase">
            Verified student context
          </p>
          <h2 className="mt-3 text-2xl font-medium">Facts the product may reuse</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            In the real product, these fields become the allowed evidence boundary for
            matching explanations and outreach. This phase stores only fictional data.
          </p>
        </div>

        <FieldGroup className="mt-7">
          <div className="grid gap-5 sm:grid-cols-2">
            <Field data-invalid={Boolean(errors.name)}>
              <FieldLabel htmlFor="name">Name</FieldLabel>
              <Input aria-invalid={Boolean(errors.name)} id="name" {...register("name")} />
              <FieldError errors={[errors.name]} />
            </Field>
            <Field data-invalid={Boolean(errors.graduationYear)}>
              <FieldLabel htmlFor="graduationYear">Graduation year</FieldLabel>
              <Input
                aria-invalid={Boolean(errors.graduationYear)}
                id="graduationYear"
                inputMode="numeric"
                {...register("graduationYear")}
              />
              <FieldError errors={[errors.graduationYear]} />
            </Field>
          </div>

          <Field data-invalid={Boolean(errors.program)}>
            <FieldLabel htmlFor="program">Programme and year</FieldLabel>
            <Input aria-invalid={Boolean(errors.program)} id="program" {...register("program")} />
            <FieldError errors={[errors.program]} />
          </Field>

          <Field data-invalid={Boolean(errors.institution)}>
            <FieldLabel htmlFor="institution">Institution</FieldLabel>
            <Input
              aria-invalid={Boolean(errors.institution)}
              id="institution"
              {...register("institution")}
            />
            <FieldDescription>Keep “fictional” in the demo institution name.</FieldDescription>
            <FieldError errors={[errors.institution]} />
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field data-invalid={Boolean(errors.researchInterests)}>
              <FieldLabel htmlFor="researchInterests">Research interests</FieldLabel>
              <Textarea
                aria-invalid={Boolean(errors.researchInterests)}
                id="researchInterests"
                rows={3}
                {...register("researchInterests")}
              />
              <FieldDescription>Separate up to six interests with commas.</FieldDescription>
              <FieldError errors={[errors.researchInterests]} />
            </Field>
            <Field data-invalid={Boolean(errors.skills)}>
              <FieldLabel htmlFor="skills">Relevant skills</FieldLabel>
              <Textarea
                aria-invalid={Boolean(errors.skills)}
                id="skills"
                rows={3}
                {...register("skills")}
              />
              <FieldDescription>Separate up to eight skills with commas.</FieldDescription>
              <FieldError errors={[errors.skills]} />
            </Field>
          </div>

          <Field data-invalid={Boolean(errors.projectTitle)}>
            <FieldLabel htmlFor="projectTitle">Most relevant project</FieldLabel>
            <Input
              aria-invalid={Boolean(errors.projectTitle)}
              id="projectTitle"
              {...register("projectTitle")}
            />
            <FieldError errors={[errors.projectTitle]} />
          </Field>

          <Field data-invalid={Boolean(errors.projectSummary)}>
            <FieldLabel htmlFor="projectSummary">What you actually built or studied</FieldLabel>
            <Textarea
              aria-invalid={Boolean(errors.projectSummary)}
              id="projectSummary"
              rows={5}
              {...register("projectSummary")}
            />
            <FieldDescription>
              Write a concrete, verifiable description. Avoid performance claims you
              cannot support.
            </FieldDescription>
            <FieldError errors={[errors.projectSummary]} />
          </Field>

          <Field data-invalid={Boolean(errors.weeklyAvailability)}>
            <FieldLabel htmlFor="weeklyAvailability">Weekly availability</FieldLabel>
            <NativeSelect
              aria-invalid={Boolean(errors.weeklyAvailability)}
              id="weeklyAvailability"
              {...register("weeklyAvailability")}
            >
              <option value="5-10 hours">5-10 hours</option>
              <option value="10-15 hours">10-15 hours</option>
              <option value="15+ hours">15+ hours</option>
            </NativeSelect>
            <FieldError errors={[errors.weeklyAvailability]} />
          </Field>
        </FieldGroup>

        <div className="mt-8 flex flex-wrap items-center gap-4 border-t border-border pt-6">
          <Button disabled={isSubmitting} type="submit" variant="evidence">
            <Save aria-hidden="true" />
            Save demo profile
          </Button>
          <p aria-live="polite" className="text-sm text-muted-foreground">
            {savedMessage || (isDirty ? "Unsaved changes" : "Profile is up to date")}
          </p>
        </div>
      </form>

      <aside className="border border-brand-teal/20 bg-brand-teal-soft/55 p-6 lg:sticky lg:top-24">
        <ShieldCheck aria-hidden="true" className="size-6 text-brand-teal" />
        <h2 className="mt-5 text-xl font-medium">Why this boundary matters</h2>
        <ul className="mt-4 space-y-3 text-sm leading-6 text-muted-foreground">
          <li>Drafts may reuse only facts visible here and selected paper evidence.</li>
          <li>No resume upload exists in this phase, so no private file is collected.</li>
          <li>Session storage is a demo convenience, not secure persistence.</li>
        </ul>
      </aside>
    </div>
  );
}

export function ProfileExperience() {
  const { hydrated } = useDemoStore();

  if (!hydrated) {
    return (
      <DataState
        description="Restoring the validated fictional profile from this browser session."
        kind="loading"
        title="Loading the demo profile"
      />
    );
  }

  return <ProfileForm />;
}
