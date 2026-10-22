"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Save, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import Link from "next/link";

import { DataState } from "@/components/states/data-state";
import { Button } from "@/components/ui/button";
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
  accountProfileFormSchema,
  accountProfileToFormValues,
  profileFormValuesToAccountProfile,
  profileErrorMessage,
  type AccountProfileFormValues,
  type AccountProfile,
} from "@/lib/api/profile";
import {
  useAccountProfile,
  useSaveAccountProfile,
} from "@/features/profile/use-account-profile";

function ProfileForm({ profile, userId }: { profile: AccountProfile; userId: string }) {
  const [savedMessage, setSavedMessage] = useState("");
  const [saveError, setSaveError] = useState("");
  const updateProfile = useSaveAccountProfile(userId);
  const {
    formState: { errors, isDirty, isSubmitting },
    handleSubmit,
    register,
    reset,
  } = useForm<AccountProfileFormValues>({
    defaultValues: accountProfileToFormValues(profile),
    resolver: zodResolver(accountProfileFormSchema),
  });

  useEffect(() => {
    reset(accountProfileToFormValues(profile));
  }, [reset, profile]);

  async function saveProfile(values: AccountProfileFormValues) {
    setSavedMessage("");
    setSaveError("");
    try {
      const savedProfile = await updateProfile.mutateAsync(profileFormValuesToAccountProfile(values));
      reset(accountProfileToFormValues(savedProfile));
      setSavedMessage("Your research profile has been saved.");
    } catch (error) {
      setSaveError(profileErrorMessage(error));
    }
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
            Your research background
          </p>
          <h2 className="mt-3 text-2xl font-medium">Facts the product may reuse</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            These fields are the allowed evidence boundary for live matching and
            outreach. Save accurate information about your own experience.
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
            <FieldDescription>Enter the institution you currently attend.</FieldDescription>
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
            {isSubmitting ? "Saving profile..." : "Save profile"}
          </Button>
          <p
            aria-live="polite"
            className={saveError ? "text-sm text-destructive" : "text-sm text-muted-foreground"}
          >
            {saveError ||
              savedMessage ||
              (isDirty ? "Unsaved changes" : "Profile is up to date")}
          </p>
        </div>
      </form>

      <aside className="border border-brand-teal/20 bg-brand-teal-soft/55 p-6 lg:sticky lg:top-24">
        <ShieldCheck aria-hidden="true" className="size-6 text-brand-teal" />
        <h2 className="mt-5 text-xl font-medium">Why this boundary matters</h2>
        <ul className="mt-4 space-y-3 text-sm leading-6 text-muted-foreground">
          <li>Drafts may reuse only facts visible here and selected paper evidence.</li>
          <li>Only add experience and skills you can explain and support.</li>
          <li>Your profile is saved to your account. You can return here to update it.</li>
        </ul>
      </aside>
    </div>
  );
}

export function ProfileExperience() {
  const profile = useAccountProfile();
  if (profile.authLoading || profile.isPending) {
    return <DataState kind="loading" title="Loading your profile" description="Retrieving your saved research background." />;
  }
  if (profile.isError) {
    return <DataState kind="error" title="Your profile is unavailable" description={profileErrorMessage(profile.error)} action={<Button onClick={() => void profile.refetch()}>Retry profile</Button>} />;
  }
  if (!profile.data || !profile.userId) {
    return <DataState kind="empty" title="Create your research profile" description="Add your background before finding mentors." action={<Link href="/onboarding" className="text-brand-teal underline">Complete your profile</Link>} />;
  }
  return <ProfileForm key={profile.userId} profile={profile.data} userId={profile.userId} />;
}
