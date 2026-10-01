import Link from "next/link";

import { ScrollProgress } from "@/features/landing/scroll-progress";
import { DemoCard } from "@/features/landing/demo-card";
import { AnimatedCounter } from "@/features/landing/animated-counter";
import { Reveal } from "@/features/landing/reveal";
import { StepsSection } from "@/features/landing/steps-section";

/* ── Static data ────────────────────────────────────────────────────────── */
const DATA_SOURCES = [
  "OpenAlex", "Semantic Scholar", "arXiv", "Crossref", "ORCID",
];

const FEATURES = [
  {
    title: "Matches you can inspect",
    body: "Every ranking links to the papers behind it and shows its score, so you can judge the match yourself.",
    visual: (
      <svg viewBox="0 0 200 96" aria-hidden="true" className="h-full w-full">
        <g stroke="var(--brand-teal)" strokeWidth="1.5" opacity=".7">
          <path d="M30 70L80 30L130 60L175 25M80 30L100 80L130 60" fill="none" />
        </g>
        <g fill="var(--brand-teal)">
          <circle className="pulse-dot" cx="30" cy="70" r="5" />
          <circle cx="80" cy="30" r="6" />
          <circle className="pulse-dot" cx="130" cy="60" r="5" style={{ animationDelay: ".8s" }} />
          <circle cx="175" cy="25" r="5" />
          <circle cx="100" cy="80" r="4" />
        </g>
      </svg>
    ),
  },
  {
    title: "Drafts that cite their sources",
    body: "Emails use only your verified profile and the papers you chose. Edit every word before you send.",
    visual: (
      <div className="p-3 text-left text-xs leading-relaxed text-muted-foreground">
        Dear Prof. Rao, your 2024 paper on sparse graph attention…
        <span className="cursor-blink" aria-hidden="true" />
      </div>
    ),
  },
  {
    title: "Internships, honestly labelled",
    body: "Availability, funding, and work mode come with a source link. If a detail is unknown, we say so.",
    visual: (
      <svg viewBox="0 0 200 96" aria-hidden="true" className="h-full w-full">
        <g fill="none" stroke="var(--border)">
          <rect x="20" y="14" width="160" height="22" rx="7" />
          <rect x="20" y="44" width="160" height="22" rx="7" />
        </g>
        <rect x="26" y="20" width="54" height="10" rx="5" fill="var(--brand-teal-soft)" />
        <rect x="26" y="50" width="38" height="10" rx="5" fill="var(--brand-teal)" />
        <text x="100" y="86" fontSize="10" fill="var(--muted-foreground)">Funding: unknown</text>
      </svg>
    ),
  },
];

const PRINCIPLES = [
  {
    wide: true,
    icon: null,
    visual: (
      <div className="flex h-16 items-center gap-3 px-4">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-border">
          <div className="bar-fill h-full w-[86%] rounded-full bg-gradient-to-r from-brand-teal-soft to-brand-teal" />
        </div>
        <span className="text-xs text-muted-foreground">paper match 86</span>
      </div>
    ),
    title: "Every match has receipts",
    body: "Each recommendation keeps its publications and source links, so you can check the claim yourself.",
  },
  {
    wide: false,
    icon: "?",
    dashed: false,
    title: "Unknown stays unknown",
    body: "We never guess availability, funding, or contact details to look complete.",
  },
  {
    wide: false,
    icon: "✓",
    dashed: true,
    title: "You press send",
    body: "Nothing goes out without your review.",
  },
  {
    wide: true,
    icon: null,
    visual: (
      <div className="h-16">
        <svg viewBox="0 0 300 70" className="h-full w-full" aria-hidden="true">
          <path
            d="M10 50C60 10 100 60 150 30S250 10 290 35"
            fill="none"
            stroke="var(--brand-teal)"
            strokeWidth="2"
            strokeDasharray="6 6"
          >
            <animate attributeName="stroke-dashoffset" to="-48" dur="3s" repeatCount="indefinite" />
          </path>
        </svg>
      </div>
    ),
    title: "AI helps, rules decide",
    body: "Language models expand your query and draft text. Scoring and ranking follow fixed, visible rules.",
  },
];

const FAQ = [
  {
    q: "Is it free?",
    a: "Yes. Creating an account and using search, matching, and drafts costs nothing.",
  },
  {
    q: "Will it email professors for me?",
    a: "No. You review and send every message yourself.",
  },
  {
    q: "Where does the data come from?",
    a: "Open sources: OpenAlex, Semantic Scholar, arXiv, Crossref, and ORCID. We don't scrape websites.",
  },
  {
    q: "What happens to my profile?",
    a: "It's used only to rank matches and write your drafts, and it stays under your control.",
  },
];

/* ── GlowCard helper ────────────────────────────────────────────────────── */
function GlowCard({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <article
      className={`glow-card rounded-2xl border border-border bg-card p-6 ${className}`}
      onPointerMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
        e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
      }}
    >
      {children}
    </article>
  );
}

/* ── Page ───────────────────────────────────────────────────────────────── */
export default function Home() {
  // Derive marquee items (repeat 4× so it loops seamlessly)
  const marqueeItems = [...DATA_SOURCES, ...DATA_SOURCES, ...DATA_SOURCES, ...DATA_SOURCES];

  return (
    <main id="main-content" className="relative z-[1]">
      {/* Ambient blobs */}
      <div aria-hidden="true" className="ambient-blob ambient-blob-1" />
      <div aria-hidden="true" className="ambient-blob ambient-blob-2" />

      {/* Scroll progress bar */}
      <ScrollProgress />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-[1160px] px-7">
        <section className="grid items-center gap-14 pb-[70px] pt-[84px] lg:grid-cols-[1.1fr_0.9fr] lg:gap-14">
          {/* Left */}
          <div>
            <h1
              aria-label="Find the professor whose papers match your questions."
              className="font-serif text-[clamp(40px,5.6vw,76px)] font-semibold leading-[1.04] tracking-[-0.025em]"
            >
              {[
                "Find", "the", "professor", "whose", "papers", "match", "your", "questions.",
              ].map((w, i) => (
                <span
                  key={i}
                  aria-hidden="true"
                  className="hero-word"
                  style={{ animationDelay: `${0.15 + i * 0.09}s` }}
                >
                  {w}{" "}
                </span>
              ))}
            </h1>

            {/* Animated arc underline */}
            <svg
              className="mt-1 block w-full max-w-[420px]"
              viewBox="0 0 420 60"
              fill="none"
              aria-hidden="true"
            >
              <path
                className="arc-path"
                d="M2 56C70 4 140 4 210 30S350 56 418 6"
                stroke="var(--brand-teal)"
                strokeWidth="3"
                strokeLinecap="round"
              />
            </svg>

            <p className="mt-6 max-w-[30em] text-[19px] text-muted-foreground">
              Research Bridge matches you with mentors using their real publications. See why each
              professor ranks where they do, then send an email you wrote and approved.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/login"
                className="inline-flex h-[46px] items-center gap-2 rounded-full bg-brand-teal px-[22px] text-[15px] font-bold text-white transition-[box-shadow] hover:shadow-[0_8px_40px_-6px_color-mix(in_srgb,var(--brand-teal)_70%,transparent)] motion-reduce:transition-none"
              >
                Create free account
              </Link>
              <Link
                href="#how"
                className="inline-flex h-[46px] items-center gap-2 rounded-full border border-border px-[22px] text-[15px] font-bold transition-colors hover:border-brand-teal motion-reduce:transition-none"
              >
                See how it works
              </Link>
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              Free for students. No credit card.
            </p>
          </div>

          {/* Right — interactive demo */}
          <DemoCard />
        </section>

        {/* ── Stats ──────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 gap-5 border-t border-border pb-12 pt-7 sm:grid-cols-3">
          <Reveal>
            <strong className="font-serif text-[clamp(30px,4vw,48px)] font-semibold leading-none">
              <AnimatedCounter value={200} suffix="M+" />
            </strong>
            <span className="mt-1 block text-sm text-muted-foreground">
              papers searchable through OpenAlex
            </span>
          </Reveal>
          <Reveal delay={100}>
            <strong className="font-serif text-[clamp(30px,4vw,48px)] font-semibold leading-none">
              <AnimatedCounter value={5} />
            </strong>
            <span className="mt-1 block text-sm text-muted-foreground">
              open scholarly sources, no scraping
            </span>
          </Reveal>
          <Reveal delay={200}>
            <strong className="font-serif text-[clamp(30px,4vw,48px)] font-semibold leading-none">
              <AnimatedCounter value={0} />
            </strong>
            <span className="mt-1 block text-sm text-muted-foreground">
              emails sent without your approval
            </span>
          </Reveal>
        </div>
      </div>

      {/* ── Marquee ──────────────────────────────────────────────────────── */}
      <div
        aria-label="Data sources"
        className="overflow-hidden border-y border-border py-[18px] [mask-image:linear-gradient(90deg,transparent,#000_12%,#000_88%,transparent)]"
      >
        <div className="marquee-track flex w-max gap-14 font-serif text-[22px] font-semibold text-muted-foreground">
          {marqueeItems.map((s, i) => (
            <span key={i}>{s}</span>
          ))}
        </div>
      </div>

      {/* ── Features ─────────────────────────────────────────────────────── */}
      <section id="features" className="py-24">
        <div className="mx-auto max-w-[1160px] px-7">
          <Reveal>
            <h2 className="font-serif text-[clamp(30px,4vw,48px)] font-semibold leading-[1.1] tracking-[-0.02em]">
              Everything between a topic and a sent email
            </h2>
          </Reveal>
          <Reveal delay={60}>
            <p className="mb-12 mt-3 max-w-[36em] text-muted-foreground">
              Search papers, compare mentors, find internships, and draft outreach in one place.
            </p>
          </Reveal>
          <div className="grid gap-5 md:grid-cols-3">
            {FEATURES.map(({ title, body, visual }, i) => (
              <Reveal key={title} delay={i * 80}>
                <GlowCard>
                  <div className="flex h-24 items-center justify-center overflow-hidden rounded-xl border border-border">
                    {visual}
                  </div>
                  <h3 className="font-serif mt-4 text-[22px] font-semibold">{title}</h3>
                  <p className="mt-2 text-muted-foreground">{body}</p>
                </GlowCard>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────── */}
      <section id="how" className="py-24">
        <div className="mx-auto max-w-[1160px] px-7">
          <Reveal>
            <h2 className="font-serif text-[clamp(30px,4vw,48px)] font-semibold leading-[1.1] tracking-[-0.02em]">
              From profile to first reply in three steps
            </h2>
          </Reveal>
          <Reveal delay={60}>
            <p className="mb-12 mt-3 max-w-[36em] text-muted-foreground">
              You stay in control at every step.
            </p>
          </Reveal>
          <StepsSection />
        </div>
      </section>

      {/* ── Principles ───────────────────────────────────────────────────── */}
      <section id="principles" className="py-24">
        <div className="mx-auto max-w-[1160px] px-7">
          <Reveal>
            <h2 className="font-serif text-[clamp(30px,4vw,48px)] font-semibold leading-[1.1] tracking-[-0.02em]">
              Rules we won't bend
            </h2>
          </Reveal>
          <Reveal delay={60}>
            <p className="mb-12 mt-3 max-w-[36em] text-muted-foreground">
              Trust matters when you're writing to someone who doesn't know you yet.
            </p>
          </Reveal>

          {/* Bento grid */}
          <div className="grid grid-cols-1 gap-5 md:grid-cols-6">
            {PRINCIPLES.map(({ wide, icon, dashed, visual, title, body }, i) => (
              <Reveal
                key={title}
                delay={i * 60}
                className={wide ? "md:col-span-4" : "md:col-span-2"}
              >
                <GlowCard className="h-full">
                  {visual ? (
                    visual
                  ) : (
                    <div
                      className={`mb-3 inline-grid size-11 place-items-center rounded-full border-2 font-serif text-[22px] font-semibold text-brand-teal ${dashed ? "border-brand-teal" : "border-dashed border-brand-teal"}`}
                    >
                      {icon}
                    </div>
                  )}
                  <h3 className="font-serif mt-2 text-[22px] font-semibold">{title}</h3>
                  <p className="mt-2 text-muted-foreground">{body}</p>
                </GlowCard>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ──────────────────────────────────────────────────────────── */}
      <section id="faq" className="py-24">
        <div className="mx-auto max-w-[1160px] px-7">
          <Reveal>
            <h2 className="font-serif mb-6 text-[clamp(30px,4vw,48px)] font-semibold leading-[1.1] tracking-[-0.02em]">
              Questions students ask
            </h2>
          </Reveal>
          <div className="max-w-[760px] divide-y divide-border">
            {FAQ.map(({ q, a }, i) => (
              <Reveal key={q} delay={i * 60}>
                <details className="group py-[18px]">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-5 font-serif text-[20px] font-semibold [&::-webkit-details-marker]:hidden">
                    {q}
                    <span
                      aria-hidden="true"
                      className="shrink-0 text-brand-teal transition-transform duration-300 group-open:rotate-45 motion-reduce:transition-none"
                    >
                      +
                    </span>
                  </summary>
                  <p className="mt-2.5 text-muted-foreground">{a}</p>
                </details>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section id="cta" className="py-24">
        <div className="mx-auto max-w-[1160px] px-7">
          <Reveal>
            <div className="relative overflow-hidden rounded-[28px] border border-border bg-card px-6 py-[72px] text-center">
              {/* Conic spin accent */}
              <div
                aria-hidden="true"
                className="conic-spin pointer-events-none absolute inset-[-40%] bg-[conic-gradient(from_0deg,transparent,color-mix(in_srgb,var(--brand-teal)_14%,transparent),transparent_40%)]"
              />
              <div className="relative z-[1]">
                <h2 className="font-serif mx-auto max-w-lg text-[clamp(30px,4vw,48px)] font-semibold leading-[1.1] tracking-[-0.02em]">
                  Your next research project starts with one search.
                </h2>
                <p className="mx-auto mt-3 max-w-[30em] text-muted-foreground">
                  Create your profile in about two minutes and see mentors matched to your
                  interests.
                </p>
                <Link
                  href="/login"
                  className="mt-7 inline-flex h-[46px] items-center gap-2 rounded-full bg-brand-teal px-[22px] text-[15px] font-bold text-white transition-[box-shadow] hover:shadow-[0_8px_40px_-6px_color-mix(in_srgb,var(--brand-teal)_70%,transparent)] motion-reduce:transition-none"
                >
                  Create free account
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="border-t border-border py-8">
        <div className="mx-auto flex max-w-[1160px] flex-wrap items-center justify-between gap-3 px-7 text-sm text-muted-foreground">
          <span>© {new Date().getFullYear()} Research Bridge</span>
          <nav aria-label="Footer" className="flex gap-5">
            <a href="#" className="hover:text-foreground transition-colors motion-reduce:transition-none">Privacy</a>
            <a href="#" className="hover:text-foreground transition-colors motion-reduce:transition-none">Terms</a>
            <a href="#" className="hover:text-foreground transition-colors motion-reduce:transition-none">Contact</a>
          </nav>
        </div>
      </footer>
    </main>
  );
}
