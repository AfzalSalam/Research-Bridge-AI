"use client";

import { useEffect } from "react";

export function ScrollProgress() {
  useEffect(() => {
    const bar = document.getElementById("scroll-prog");
    const hd = document.getElementById("site-header");

    function onScroll() {
      const y = window.scrollY;
      const max =
        document.documentElement.scrollHeight - window.innerHeight;
      if (bar) bar.style.transform = `scaleX(${y / Math.max(1, max)})`;
      if (hd) hd.classList.toggle("scrolled", y > 10);
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div
      id="scroll-prog"
      aria-hidden="true"
      className="pointer-events-none fixed left-0 top-0 z-[60] h-[3px] w-full origin-left scale-x-0 bg-brand-teal"
    />
  );
}
