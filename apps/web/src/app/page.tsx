import {
  ArrowRight,
  ArrowUpRight,
  BookCheck,
  Briefcase,
  FileSearch,
  Lock,
  Mail,
  Share2,
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

const stats = [
  { icon: Users, stat: "10,000+", label: "Professors discoverable" },
  { icon: FileSearch, stat: "200M+", label: "Papers indexed via OpenAlex" },
  { icon: ShieldCheck, stat: "100%", label: "Evidence-backed matches" },
];

export default function Home() {
  return (
    <main id="main-content">
      {/* ── Hero ── */}
      <section className="relative border-b border-border overflow-hidden">
        <Container className="grid min-h-[calc(100svh-4.5rem)] items-center gap-14 py-16 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)] lg:gap-16 lg:py-24">
          {/* Left: text content */}
          <div className="max-w-3xl">
            {/* Eyebrow with coloured bars */}
            <div className="flex items-center gap-3">
              <span className="flex gap-1" aria-hidden="true">
                <span className="block h-4 w-1 rounded-full bg-blue-500" />
                <span className="block h-4 w-1 rounded-full bg-brand-teal" />
                <span className="block h-4 w-1 rounded-full bg-yellow-400" />
              </span>
              <p className="text-xs font-bold tracking-[0.2em] text-muted-foreground uppercase">
                AI-Powered Research Discovery for Students
              </p>
            </div>

            <h1 className="mt-6 text-[clamp(2.75rem,6vw,5.75rem)] leading-[0.93] font-extrabold tracking-[-0.04em]">
              Find your perfect{" "}
              <span className="text-brand-teal">
                research mentor.
              </span>
            </h1>

            <p className="mt-8 max-w-xl text-base leading-7 text-muted-foreground sm:text-lg sm:leading-8">
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

            <p className="mt-5 flex items-center gap-1.5 text-xs text-muted-foreground">
              <Lock aria-hidden="true" className="size-3" />
              Free to use · No credit card required
            </p>
          </div>

          {/* Right: stats card widget */}
          <aside
            aria-label="Platform highlights"
            className="hidden lg:block"
          >
            <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-lg">
              {/* Card header */}
              <div className="flex items-start justify-between border-b border-border px-5 pt-5 pb-4">
                <div>
                  <p className="text-[10px] font-bold tracking-[0.18em] text-brand-teal uppercase">
                    Research Bridge / Index
                  </p>
                  <p className="mt-1 text-lg font-semibold">Connected evidence</p>
                </div>
                <button
                  aria-label="Share"
                  className="grid size-8 place-items-center rounded-full border border-border text-muted-foreground transition-colors hover:text-foreground"
                >
                  <Share2 aria-hidden="true" className="size-3.5" />
                </button>
              </div>

              {/* Constellation visualisation placeholder */}
              <div className="relative flex h-44 items-center justify-center overflow-hidden bg-gradient-to-br from-purple-950/40 via-background to-emerald-950/30">
                <svg
                  aria-hidden="true"
                  className="absolute inset-0 h-full w-full opacity-60"
                  viewBox="0 0 400 176"
                >
                  {/* Edges */}
                  {[
                    [200, 88, 120, 40], [200, 88, 280, 40], [200, 88, 320, 100],
                    [200, 88, 80, 120], [200, 88, 260, 150], [120, 40, 60, 70],
                    [280, 40, 340, 30], [80, 120, 40, 150], [320, 100, 360, 140],
                  ].map(([x1, y1, x2, y2], i) => (
                    <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
                      stroke="url(#edgeGrad)" strokeWidth="0.8" strokeOpacity="0.6" />
                  ))}
                  {/* Nodes */}
                  {[
                    [200, 88, 6, "#C8FF00"], [120, 40, 4, "#A78BFA"], [280, 40, 4, "#A78BFA"],
                    [320, 100, 3.5, "#34D399"], [80, 120, 3.5, "#34D399"],
                    [260, 150, 3, "#A78BFA"], [60, 70, 2.5, "#A78BFA"],
                    [340, 30, 2.5, "#34D399"], [40, 150, 2, "#A78BFA"],
                    [360, 140, 2, "#34D399"],
                  ].map(([cx, cy, r, fill], i) => (
                    <circle key={i} cx={cx} cy={cy} r={r} fill={fill as string} fillOpacity="0.9" />
                  ))}
                  <defs>
                    <linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#A78BFA" stopOpacity="0.8" />
                      <stop offset="100%" stopColor="#34D399" stopOpacity="0.8" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>

              {/* Stats rows */}
              <div className="divide-y divide-border">
                {stats.map(({ icon: Icon, stat, label }) => (
                  <div
                    key={label}
                    className="flex items-center gap-3 px-5 py-3.5"
                  >
                    <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-surface-subtle text-brand-teal">
                      <Icon aria-hidden="true" className="size-4" strokeWidth={1.7} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-base font-bold leading-none">{stat}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{label}</p>
                    </div>
                    <ArrowUpRight aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
                  </div>
                ))}
              </div>
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
              className="mt-4 text-3xl font-bold tracking-[-0.025em] sm:text-4xl"
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
                className="group rounded-xl border border-border bg-card p-7 transition-all hover:border-brand-teal/30 hover:shadow-md motion-reduce:transition-none"
              >
                <span className="grid size-12 place-items-center rounded-lg bg-brand-teal-soft text-brand-teal transition-colors group-hover:bg-brand-teal group-hover:text-card motion-reduce:transition-none">
                  <Icon aria-hidden="true" className="size-6" strokeWidth={1.7} />
                </span>
                <h3 className="mt-5 text-xl font-bold">{title}</h3>
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
              className="mt-4 text-3xl font-bold tracking-[-0.025em] sm:text-4xl"
              id="how-it-works-title"
            >
              Three steps to your next opportunity
            </h2>
          </div>

          <div className="mx-auto mt-14 grid max-w-4xl gap-8 md:grid-cols-3">
            {steps.map(({ step, title, description }) => (
              <div key={step} className="text-center">
                <span className="mx-auto grid size-14 place-items-center rounded-full bg-brand-teal text-card text-lg font-bold">
                  {step}
                </span>
                <h3 className="mt-5 text-lg font-bold">{title}</h3>
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
              className="mt-4 text-3xl font-bold tracking-[-0.025em] sm:text-4xl"
              id="principles-title"
            >
              Designed to make evidence easier to inspect
            </h2>
          </div>

          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {principles.map(({ icon: Icon, title, description }) => (
              <article
                key={title}
                className="rounded-xl border border-border bg-card p-6"
              >
                <Icon
                  aria-hidden="true"
                  className="size-6 text-brand-teal"
                  strokeWidth={1.7}
                />
                <h3 className="mt-4 text-base font-bold">{title}</h3>
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
                <p className="text-lg font-bold tracking-tight text-foreground">
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
          <div className="relative overflow-hidden rounded-2xl bg-primary px-8 py-16 text-center text-primary-foreground sm:px-16">
            {/* Subtle glow in dark mode */}
            <div aria-hidden="true" className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br from-brand-teal/5 via-transparent to-purple-900/10" />
            <h2
              className="relative mx-auto max-w-lg text-3xl font-bold tracking-tight text-primary-foreground sm:text-4xl"
              id="cta-title"
            >
              Start discovering research opportunities today
            </h2>
            <p className="relative mx-auto mt-4 max-w-md text-primary-foreground/70">
              Create your free account, complete your profile, and let
              evidence-backed matching connect you with professors in your field.
            </p>
            <div className="relative mt-8 flex flex-wrap justify-center gap-3">
              <Button asChild size="lg" variant="evidence">
                <Link href="/login">
                  Sign Up Free
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            </div>
            <p className="relative mt-4 text-xs text-primary-foreground/50">
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
            <Link href="/login" className="hover:text-foreground transition-colors motion-reduce:transition-none">
              Sign In
            </Link>
            <Link href="/design-system" className="hover:text-foreground transition-colors motion-reduce:transition-none">
              Design System
            </Link>
          </nav>
        </Container>
      </footer>
    </main>
  );
}
