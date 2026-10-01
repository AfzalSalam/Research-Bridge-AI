"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

const DEMO_DATA: Record<
  string,
  Array<{
    name: string;
    dept: string;
    score: number;
    topic: string;
    bars: Array<[string, number]>;
  }>
> = {
  "Graph neural networks": [
    {
      name: "Prof. A. Rao",
      dept: "Institute of Computing",
      score: 92,
      topic: "Sparse attention on large graphs",
      bars: [["Paper match", 94], ["Recency", 88], ["Citations", 79], ["Topic overlap", 90]],
    },
    {
      name: "Prof. L. Moreau",
      dept: "Dept. of Data Science",
      score: 84,
      topic: "Graph learning for molecules",
      bars: [["Paper match", 85], ["Recency", 80], ["Citations", 90], ["Topic overlap", 72]],
    },
    {
      name: "Prof. J. Okafor",
      dept: "School of Engineering",
      score: 76,
      topic: "Temporal graph models",
      bars: [["Paper match", 74], ["Recency", 92], ["Citations", 60], ["Topic overlap", 70]],
    },
  ],
  "CRISPR base editing": [
    {
      name: "Prof. S. Lindqvist",
      dept: "Molecular Biology",
      score: 90,
      topic: "Precision editors in vivo",
      bars: [["Paper match", 92], ["Recency", 90], ["Citations", 85], ["Topic overlap", 88]],
    },
    {
      name: "Prof. M. Iyer",
      dept: "Genetics",
      score: 81,
      topic: "Off-target detection",
      bars: [["Paper match", 80], ["Recency", 75], ["Citations", 92], ["Topic overlap", 78]],
    },
    {
      name: "Prof. T. Park",
      dept: "Biomedical Eng.",
      score: 73,
      topic: "Delivery vectors",
      bars: [["Paper match", 70], ["Recency", 88], ["Citations", 58], ["Topic overlap", 72]],
    },
  ],
  "Climate modelling": [
    {
      name: "Prof. E. Haddad",
      dept: "Earth Sciences",
      score: 89,
      topic: "Regional downscaling",
      bars: [["Paper match", 90], ["Recency", 84], ["Citations", 88], ["Topic overlap", 86]],
    },
    {
      name: "Prof. N. Berg",
      dept: "Atmospheric Physics",
      score: 82,
      topic: "Extreme rainfall",
      bars: [["Paper match", 82], ["Recency", 78], ["Citations", 86], ["Topic overlap", 80]],
    },
    {
      name: "Prof. K. Das",
      dept: "Environmental Eng.",
      score: 71,
      topic: "Urban heat models",
      bars: [["Paper match", 68], ["Recency", 90], ["Citations", 55], ["Topic overlap", 70]],
    },
  ],
};

const TOPICS = Object.keys(DEMO_DATA);

function MentorCard({
  mentor,
  defaultOpen,
  delay,
}: {
  mentor: (typeof DEMO_DATA)[string][number];
  defaultOpen: boolean;
  delay: number;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={open}
      onClick={() => setOpen((o) => !o)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setOpen((o) => !o); }
      }}
      className="cursor-pointer rounded-2xl border border-border p-3 transition-colors hover:border-brand-teal motion-reduce:transition-none"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-bold">{mentor.name}</span>
        <span className="text-sm font-bold text-brand-teal">{mentor.score}</span>
      </div>
      <p className="mt-0.5 text-xs text-muted-foreground">
        {mentor.dept} · {mentor.topic}
      </p>

      {/* Score bars */}
      <div
        className={cn(
          "overflow-hidden transition-all duration-400 motion-reduce:transition-none",
          open ? "max-h-40 mt-2" : "max-h-0",
        )}
      >
        <div className="space-y-1.5">
          {mentor.bars.map(([label, val]) => (
            <div key={label} className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="w-24 shrink-0 font-medium">{label}</span>
              <span className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-border">
                <span
                  className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-brand-teal-soft to-brand-teal"
                  style={{ width: `${val}%` }}
                />
              </span>
              <span className="w-6 text-right">{val}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function DemoCard() {
  const [topic, setTopic] = useState(TOPICS[0]);
  const cardRef = useRef<HTMLElement>(null);

  // 3-D tilt on hover
  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!window.matchMedia("(hover: hover)").matches) return;

    function onMove(e: PointerEvent) {
      const r = card!.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      card!.style.transform = `perspective(900px) rotateY(${x * 7}deg) rotateX(${-y * 7}deg)`;
    }
    function onLeave() {
      card!.style.transform = "";
    }

    card.addEventListener("pointermove", onMove as EventListener);
    card.addEventListener("pointerleave", onLeave);
    return () => {
      card.removeEventListener("pointermove", onMove as EventListener);
      card.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  const mentors = DEMO_DATA[topic] ?? [];

  return (
    <aside
      ref={cardRef}
      aria-label="Interactive example"
      className="rounded-3xl border border-border bg-card p-5 shadow-[0_30px_80px_-30px_rgba(10,15,50,0.4)] transition-transform duration-150 motion-reduce:transition-none"
    >
      <h2 className="font-serif text-lg font-semibold">Try a topic</h2>
      <p className="mt-0.5 text-xs text-muted-foreground">
        Sample data for illustration. Tap a mentor to see the score.
      </p>

      {/* Topic chips */}
      <div role="group" aria-label="Topics" className="mt-3 flex flex-wrap gap-2">
        {TOPICS.map((t) => (
          <button
            key={t}
            aria-pressed={topic === t}
            onClick={() => setTopic(t)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors motion-reduce:transition-none",
              topic === t
                ? "border-transparent bg-brand-teal text-white"
                : "border-border bg-transparent hover:border-brand-teal",
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Mentor cards */}
      <div className="mt-3 space-y-2" aria-live="polite">
        {mentors.map((m, i) => (
          <MentorCard key={m.name} mentor={m} defaultOpen={i === 0} delay={i * 100} />
        ))}
      </div>
    </aside>
  );
}
