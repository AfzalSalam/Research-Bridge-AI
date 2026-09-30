"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/features/demo/components/native-select";
import { Textarea } from "@/components/ui/textarea";
import { 
  updateAccountProfile, 
  accountProfileSchema, 
  accountProfileFormSchema,
  type AccountProfile,
  type AccountProfileFormValues
} from "@/lib/api/profile";
import { ShieldCheck, ArrowRight } from "lucide-react";

function commaSeparatedValues(value: string | string[]): string[] {
  if (Array.isArray(value)) return value;
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

export function OnboardingExperience() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [saveError, setSaveError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AccountProfileFormValues>({
    resolver: zodResolver(accountProfileFormSchema),
    defaultValues: {
      name: "",
      program: "",
      institution: "",
      graduationYear: "",
      researchInterests: "",
      skills: "",
      projectTitle: "",
      projectSummary: "",
      weeklyAvailability: "10-15 hours",
    },
  });

  const updateProfile = useMutation({
    mutationFn: (data: AccountProfile) => updateAccountProfile(data),
    onSuccess: (savedProfile) => {
      queryClient.setQueryData(["profile"], savedProfile);
      router.push("/discover");
    },
    onError: (error) => {
      setSaveError(error instanceof Error ? error.message : "Failed to save profile.");
    },
  });

  async function saveProfile(values: AccountProfileFormValues) {
    setSaveError("");
    const profile = accountProfileSchema.parse({
      ...values,
      researchInterests: commaSeparatedValues(values.researchInterests),
      skills: commaSeparatedValues(values.skills),
    });

    await updateProfile.mutateAsync(profile);
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start max-w-6xl mx-auto">
      <form
        className="border border-border bg-surface p-5 sm:p-8 rounded-lg shadow-sm"
        noValidate
        onSubmit={handleSubmit(saveProfile)}
      >
        <div className="border-b border-border pb-6">
          <p className="text-xs font-bold tracking-[0.14em] text-brand-teal uppercase">
            Welcome to Research Bridge
          </p>
          <h2 className="mt-3 text-2xl font-medium">Complete your student profile</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            This information sets the foundation for your research matches and forms the basis
            of any outreach drafts we generate on your behalf.
          </p>
        </div>

        <FieldGroup className="mt-7">
          <div className="grid gap-5 sm:grid-cols-2">
            <Field data-invalid={Boolean(errors.name)}>
              <FieldLabel htmlFor="name">Full Name</FieldLabel>
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
            <FieldLabel htmlFor="program">Programme and year (e.g. BSc Computer Science, Year 3)</FieldLabel>
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
            {isSubmitting ? "Saving profile..." : "Continue to Dashboard"}
            {!isSubmitting && <ArrowRight aria-hidden="true" className="ml-2 size-4" />}
          </Button>
          <p
            aria-live="polite"
            className={saveError ? "text-sm text-destructive" : "text-sm text-muted-foreground"}
          >
            {saveError}
          </p>
        </div>
      </form>

      <aside className="border border-brand-teal/20 bg-brand-teal-soft/55 p-6 rounded-lg lg:sticky lg:top-24">
        <ShieldCheck aria-hidden="true" className="size-6 text-brand-teal" />
        <h2 className="mt-5 text-xl font-medium">Privacy & Security</h2>
        <ul className="mt-4 space-y-3 text-sm leading-6 text-muted-foreground">
          <li>Your profile is strictly isolated to your own account.</li>
          <li>Outreach drafts will only reuse the facts provided here.</li>
          <li>No raw resumes are processed, ensuring full control over what is shared with professors.</li>
        </ul>
      </aside>
    </div>
  );
}
