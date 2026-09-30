import {
  ArrowRight,
  BookCheck,
  Briefcase,
  FileSearch,
  Mail,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";

import { Container } from "@/components/layout/container";
import { Button } from "@/components/ui/button";

const features = [
  {
    icon: FileSearch,
    title: "Evidence-Based Matching",
    description:
      "Search real academic papers from OpenAlex and discover professors whose published work aligns with your interests — ranked by deterministic, transparent scoring.",
  },
  {
    icon: Mail,
    title: "Smart Outreach Drafts",
    description:
      "Generate personalised email drafts grounded only in your verified profile facts and the papers you selected. Every claim traces back to its source.",
  },
  {
    icon: Briefcase,
    title: "Research Internships",
    description:
      "Browse curated, source-linked research opportunities with honest availability, funding, and work-mode labels. Unknown details stay unknown.",
  },
];

const steps = [
  {
    step: "01",
    title: "Complete your profile",
    description:
      "Add your research interests, skills, and a brief project summary. This becomes the evidence boundary for all matches and drafts.",
  },
  {
    step: "02",
    title: "Discover papers & mentors",
    description:
      "Enter a research topic and receive ranked professors backed by their real publications. Inspect every score and source link.",
  },
  {
    step: "03",
    title: "Review & reach out",
    description:
      "Select your evidence, generate a grounded draft, edit it to your voice, and send it when you are ready. Never automatic, always human-approved.",
  },
];

const trustSources = [
  { name: "OpenAlex", description: "Open catalog of scholarly works" },
  { name: "Semantic Scholar", description: "AI-powered research tool" },
  { name: "arXiv", description: "Open-access research archive" },
  { name: "Crossref", description: "DOI registration agency" },
  { name: "ORCID", description: "Researcher identity registry" },
];

const principles = [
  {
    icon: FileSearch,
    title: "Paper-led discovery",
    description:
      "Every recommendation retains the publications and source links that support it.",
  },
  {
    icon: ShieldCheck,
    title: "Unknown stays unknown",
    description:
      "Availability, funding, and contact details are never guessed for polish.",
  },
  {
    icon: BookCheck,
    title: "Human-approved outreach",
    description:
      "You select the mentor and evidence, then review every editable draft before sending.",
  },
  {
    icon: Sparkles,
    title: "AI assists, never decides",
    description:
      "LLMs help expand queries and draft emails. Scoring, ranking, and sending stay deterministic and under your control.",
  },
];

export default function Home() {
  return (
    <main id="main-content">
      {/* ── Hero ── */}
      <section className="border-b border-border">
        <Container className="grid min-h-[calc(100svh-4.5rem)] items-center gap-14 py-16 lg:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.6fr)] lg:gap-20 lg:py-24">
          <div className="max-w-3xl">
            <p className="text-xs font-bold tracking-[0.2em] text-brand-teal uppercase">
              AI-powered research discovery for students
            </p>
            <h1 className="mt-6 max-w-[18ch] text-[clamp(2.75rem,5.5vw,5.5rem)] leading-[0.94] font-normal tracking-[-0.04em]">
              Find your perfect research mentor.
            </h1>
            <p className="mt-8 max-w-2xl text-lg leading-8 text-muted-foreground sm:text-xl sm:leading-9">
              Research Bridge AI matches you with professors based on real paper
              evidence — not guesswork. Discover publications, inspect every
              score, and send outreach you fully control.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Button asChild size="lg" variant="evidence">
                <Link href="/login">
                  Get Started Free
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="#how-it-works">See How It Works</Link>
              </Button>
            </div>
            <p className="mt-5 text-xs text-muted-foreground">
              Free to use · No credit card required
            </p>
          </div>

          <aside
            className="hidden rounded-xl border border-brand-teal/15 bg-gradient-to-br from-brand-teal-soft/80 via-surface to-brand-indigo-soft/50 p-8 shadow-sm lg:block"
            aria-label="Platform highlights"
          >
            <div className="space-y-6">
              {[
                {
                  icon: Users,
                  stat: "10,000+",
                  label: "Professors discoverable",
                },
                {
                  icon: FileSearch,
                  stat: "200M+",
                  label: "Papers indexed via OpenAlex",
                },
                {
                  icon: ShieldCheck,
                  stat: "100%",
                  label: "Evidence-backed matches",
                },
              ].map(({ icon: Icon, stat, label }) => (
                <div key={label} className="flex items-start gap-4">
                  <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-brand-teal/10">
                    <Icon
                      aria-hidden="true"
                      className="size-5 text-brand-teal"
                      strokeWidth={1.7}
                    />
                  </span>
                  <div>
                    <p className="text-2xl font-semibold tracking-tight">
                      {stat}
                    </p>
                    <p className="text-sm text-muted-foreground">{label}</p>
                  </div>
                </div>
              ))}
            </div>
          </aside>
        </Container>
      </section>

      {/* ── Features ── */}
      <section aria-labelledby="features-title">
        <Container className="py-[var(--section-space)]">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-xs font-bold tracking-[0.18em] text-brand-teal uppercase">
              Core features
            </p>
            <h2
              className="mt-4 text-3xl font-medium tracking-[-0.025em] sm:text-4xl"
              id="features-title"
            >
              Everything you need to land a research position
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
              From paper discovery to professor outreach, Research Bridge AI
              covers the full workflow while keeping every step transparent and
              evidence-grounded.
            </p>
          </div>

          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {features.map(({ icon: Icon, title, description }) => (
              <article
                key={title}
                className="group rounded-xl border border-border bg-surface p-7 transition-shadow hover:shadow-md motion-reduce:transition-none"
              >
                <span className="grid size-12 place-items-center rounded-lg bg-brand-teal-soft text-brand-teal transition-colors group-hover:bg-brand-teal group-hover:text-white motion-reduce:transition-none">
                  <Icon aria-hidden="true" className="size-6" strokeWidth={1.7} />
                </span>
                <h3 className="mt-5 text-xl font-medium">{title}</h3>
                <p className="mt-2 leading-7 text-muted-foreground">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </Container>
      </section>

      {/* ── How It Works ── */}
      <section
        aria-labelledby="how-it-works-title"
        className="border-y border-border bg-surface-subtle"
        id="how-it-works"
      >
        <Container className="py-[var(--section-space)]">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-xs font-bold tracking-[0.18em] text-brand-teal uppercase">
              How it works
            </p>
            <h2
              className="mt-4 text-3xl font-medium tracking-[-0.025em] sm:text-4xl"
              id="how-it-works-title"
            >
              Three steps to your next opportunity
            </h2>
          </div>

          <div className="mx-auto mt-14 grid max-w-4xl gap-8 md:grid-cols-3">
            {steps.map(({ step, title, description }) => (
              <div key={step} className="text-center">
                <span className="mx-auto grid size-14 place-items-center rounded-full bg-brand-teal text-lg font-bold text-white">
                  {step}
                </span>
                <h3 className="mt-5 text-lg font-medium">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {description}
                </p>
              </div>
            ))}
          </div>
        </Container>
      </section>

      {/* ── Principles ── */}
      <section aria-labelledby="principles-title">
        <Container className="py-[var(--section-space)]">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-xs font-bold tracking-[0.18em] text-brand-teal uppercase">
              Our principles
            </p>
            <h2
              className="mt-4 text-3xl font-medium tracking-[-0.025em] sm:text-4xl"
              id="principles-title"
            >
              Designed to make evidence easier to inspect
            </h2>
          </div>

          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {principles.map(({ icon: Icon, title, description }) => (
              <article
                key={title}
                className="rounded-xl border border-border bg-surface p-6"
              >
                <Icon
                  aria-hidden="true"
                  className="size-6 text-brand-indigo"
                  strokeWidth={1.7}
                />
                <h3 className="mt-4 text-base font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </Container>
      </section>

      {/* ── Trust Bar ── */}
      <section
        aria-labelledby="trust-title"
        className="border-y border-border bg-surface-subtle"
      >
        <Container className="py-12 text-center md:py-16">
          <p
            className="text-xs font-bold tracking-[0.18em] text-brand-teal uppercase"
            id="trust-title"
          >
            Built on real academic APIs
          </p>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            We source data exclusively from trusted, open academic databases — never scraping or guessing.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
            {trustSources.map(({ name, description }) => (
              <div key={name} className="text-center">
                <p className="text-lg font-semibold tracking-tight text-foreground">
                  {name}
                </p>
                <p className="text-xs text-muted-foreground">{description}</p>
              </div>
            ))}
          </div>
        </Container>
      </section>

      {/* ── Bottom CTA ── */}
      <section aria-labelledby="cta-title">
        <Container className="py-[var(--section-space)]">
          <div className="overflow-hidden rounded-2xl bg-primary px-8 py-16 text-center text-primary-foreground sm:px-16">
            <h2
              className="mx-auto max-w-lg text-3xl font-medium tracking-tight text-primary-foreground sm:text-4xl"
              id="cta-title"
            >
              Start discovering research opportunities today
            </h2>
            <p className="mx-auto mt-4 max-w-md text-primary-foreground/70">
              Create your free account, complete your profile, and let
              evidence-backed matching connect you with professors in your field.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Button asChild size="lg" variant="evidence">
                <Link href="/login">
                  Sign Up Free
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            </div>
            <p className="mt-4 text-xs text-primary-foreground/50">
              No credit card required · Takes less than 2 minutes
            </p>
          </div>
        </Container>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border">
        <Container className="flex flex-col items-center justify-between gap-4 py-8 text-sm text-muted-foreground sm:flex-row">
          <p>&copy; {new Date().getFullYear()} Research Bridge AI. All rights reserved.</p>
          <nav aria-label="Footer" className="flex gap-6">
            <Link href="/login" className="hover:text-foreground transition-colors">
              Sign In
            </Link>
            <Link href="/design-system" className="hover:text-foreground transition-colors">
              Design System
            </Link>
          </nav>
        </Container>
      </footer>
    </main>
  );
}
