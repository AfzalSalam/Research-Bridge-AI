"use client";

import { useEffect, useRef } from "react";

export function StepsSection() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) { el.classList.add("steps-in"); return; }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("steps-in");
          observer.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const steps = [
    {
      n: "1",
      title: "Build your profile",
      body: "Add your interests, skills, and a short project summary. Matches and drafts never go beyond it.",
    },
    {
      n: "2",
      title: "Search a topic",
      body: "Get professors ranked by their real publications. Open any score to see how it was calculated.",
    },
    {
      n: "3",
      title: "Review and send",
      body: "Pick your evidence, edit the draft, and send it yourself.",
    },
  ];

  return (
    <div ref={ref} className="steps-wrapper relative grid grid-cols-1 gap-8 md:grid-cols-3">
      {/* Animated connector line — injected via CSS on .steps-in */}
      <div
        aria-hidden="true"
        className="steps-line pointer-events-none absolute left-[8%] right-[8%] top-7 hidden h-0.5 origin-left scale-x-0 bg-gradient-to-r from-brand-teal to-brand-teal-soft md:block"
      />
      {steps.map(({ n, title, body }) => (
        <div key={n} className="relative text-center md:text-left">
          <div className="relative mx-auto mb-5 grid size-14 place-items-center rounded-full border-2 border-brand-teal bg-background font-serif text-2xl font-semibold md:mx-0">
            {n}
          </div>
          <h3 className="font-serif text-xl font-semibold">{title}</h3>
          <p className="mt-2 text-muted-foreground">{body}</p>
        </div>
      ))}
    </div>
  );
}
