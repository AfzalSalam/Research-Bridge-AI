import type { Metadata } from "next";
import type { ReactNode } from "react";
import { ArrowLeft, ArrowRight, Save } from "lucide-react";
import Link from "next/link";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { DataState } from "@/components/states/data-state";
import { StatusBadge } from "@/components/status/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

export const metadata: Metadata = {
  title: "Design System",
  description: "The internal visual and interaction reference for Research Bridge AI.",
};

const colorTokens = [
  { className: "bg-background", label: "Canvas", value: "#FCFAF8" },
  { className: "bg-surface", label: "Surface", value: "#FFFFFF" },
  { className: "bg-foreground", label: "Ink", value: "#1A1A19" },
  { className: "bg-brand-teal", label: "Evidence teal", value: "#1A746B" },
  { className: "bg-brand-indigo", label: "Structure indigo", value: "#3B426E" },
  { className: "bg-warning", label: "Unknown", value: "#8A5A12" },
] as const;

function GallerySection({
  children,
  description,
  title,
}: {
  children: ReactNode;
  description: string;
  title: string;
}) {
  return (
    <section className="border-t border-border py-12 sm:py-16">
      <div className="grid gap-8 lg:grid-cols-[16rem_minmax(0,1fr)] lg:gap-12">
        <header>
          <h2 className="text-2xl font-medium tracking-[-0.025em]">{title}</h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        </header>
        <div className="min-w-0">{children}</div>
      </div>
    </section>
  );
}

export default function DesignSystemPage() {
  return (
    <main id="main-content">
      <Container className="py-12 sm:py-16 lg:py-20">
        <PageHeader
          actions={
            <Button asChild variant="outline">
              <Link href="/">
                <ArrowLeft aria-hidden="true" />
                Back to overview
              </Link>
            </Button>
          }
          description="A living reference for the product's editorial typography, evidence-aware color language, interaction states, and responsive primitives."
          eyebrow="Internal reference"
          title="Research Bridge visual system"
        />

        <GallerySection
          description="Source Serif gives research content an editorial voice. Manrope keeps controls and supporting text precise."
          title="Typography"
        >
          <div className="space-y-8">
            <div>
              <p className="text-xs font-bold tracking-[0.14em] text-brand-teal uppercase">
                Display · Source Serif 4
              </p>
              <p className="mt-3 max-w-3xl font-serif text-4xl leading-[1.04] font-medium tracking-[-0.04em] sm:text-6xl">
                Evidence makes a recommendation worth trusting.
              </p>
            </div>
            <div>
              <p className="text-xs font-bold tracking-[0.14em] text-brand-indigo uppercase">
                Interface · Manrope
              </p>
              <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
                Clear hierarchy, readable measures, and restrained emphasis keep
                dense academic information approachable across screen sizes.
              </p>
            </div>
          </div>
        </GallerySection>

        <GallerySection
          description="Teal communicates grounded evidence; indigo structures the interface. Warm neutrals carry most of the visual weight."
          title="Color tokens"
        >
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {colorTokens.map((token) => (
              <li className="border border-border bg-surface p-3" key={token.label}>
                <div
                  aria-hidden="true"
                  className={`h-20 border border-black/10 ${token.className}`}
                />
                <div className="mt-3 flex items-baseline justify-between gap-3">
                  <span className="text-sm font-semibold">{token.label}</span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {token.value}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </GallerySection>

        <GallerySection
          description="Controls use a consistent 44-pixel default target. Status language distinguishes verified evidence from missing or uncertain facts."
          title="Actions and status"
        >
          <div className="space-y-8">
            <div className="flex flex-wrap gap-3">
              <Button type="button">
                Continue
                <ArrowRight aria-hidden="true" />
              </Button>
              <Button type="button" variant="evidence">
                <Save aria-hidden="true" />
                Save evidence
              </Button>
              <Button type="button" variant="outline">
                Secondary action
              </Button>
              <Button disabled type="button">
                Disabled
              </Button>
            </div>
            <Separator />
            <div className="flex flex-wrap gap-3">
              <StatusBadge tone="evidence">Source verified</StatusBadge>
              <StatusBadge tone="unknown">Availability unknown</StatusBadge>
              <StatusBadge tone="neutral">Draft</StatusBadge>
              <StatusBadge tone="error">Source failed</StatusBadge>
              <Badge variant="default">Research context</Badge>
            </div>
          </div>
        </GallerySection>

        <GallerySection
          description="Labels, descriptions, focus states, and explicit invalid semantics are part of the component contract."
          title="Form controls"
        >
          <div className="max-w-2xl border border-border bg-surface p-6 sm:p-8">
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="gallery-interest">Research interest</FieldLabel>
                <Input
                  id="gallery-interest"
                  placeholder="e.g. trustworthy retrieval systems"
                  readOnly
                />
                <FieldDescription>
                  A concise topic gives discovery a clear starting point.
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="gallery-context">Supporting context</FieldLabel>
                <Textarea
                  id="gallery-context"
                  placeholder="Describe the evidence you would want a mentor match to include."
                  readOnly
                />
                <FieldDescription>
                  Product forms will use React Hook Form and Zod when their data
                  contracts exist.
                </FieldDescription>
              </Field>
            </FieldGroup>
          </div>
        </GallerySection>

        <GallerySection
          description="Every data-bearing screen must explain what is happening, including partial and unavailable responses."
          title="Data states"
        >
          <div className="grid gap-5 xl:grid-cols-2">
            <DataState
              description="The request is in progress without pretending that results already exist."
              kind="loading"
              title="Gathering academic evidence"
            />
            <DataState
              description="A completed request returned no matching records."
              kind="empty"
              title="No papers matched this query"
            />
            <DataState
              description="Some sources responded, so usable evidence stays visible with a clear warning."
              kind="partial"
              title="One academic source is delayed"
            />
            <DataState
              description="The request failed and the interface should offer a safe recovery path."
              kind="error"
              title="Evidence could not be loaded"
            />
            <DataState
              className="xl:col-span-2"
              description="A fact was not present in a verified source and remains explicitly unknown."
              kind="unavailable"
              title="Funding information is unavailable"
            />
          </div>
        </GallerySection>

        <GallerySection
          description="Skeletons mirror the future content hierarchy and stop animating when reduced motion is requested."
          title="Loading structure"
        >
          <div className="max-w-2xl border border-border bg-surface p-6 sm:p-8">
            <div className="flex items-center gap-4">
              <Skeleton className="size-12 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-2/5" />
                <Skeleton className="h-3 w-3/5" />
              </div>
            </div>
            <Separator className="my-6" />
            <div className="space-y-3">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-[92%]" />
              <Skeleton className="h-4 w-4/5" />
            </div>
          </div>
        </GallerySection>
      </Container>
    </main>
  );
}
