# Direct university website discovery — approved 2026-10-07

## Scope
A separate direct-website scan on Discover, not OpenAlex enrichment. Student chooses
10, 20, or 30 unique relevant papers and approved universities. Start with KAUST,
OIST, ISTA, and IIT Gandhinagar (seasonal calls must remain honestly closed).
Follow official program/research links; show sourced publication citations and
internship program evidence, including explicit Remote/On-site/Hybrid/Not specified.
Do not infer Indian preference, professor availability, or work mode.

## Execution
1. Add typed contracts, a reviewed official-domain/source registry, and deterministic HTML
   extraction. Beautiful Soup is the single new dependency, for robust HTML parsing.
2. Add HTTPS-only pinned-public-IP fetching, redirect revalidation, robots enforcement,
   per-host delays, rate-limit stop, bounded bytes/pages/depth/time, and cancellation.
   No arbitrary user URLs, browser automation, Google Scholar, PDFs, or paywall bypass.
3. Stream scan snapshots with found/requested counts, source failures, time budget,
   partial results, source URLs, and timestamps. No fake progress percentages.
4. Add an accessible UI using React Hook Form/Zod and TanStack Query. Work-mode
   filters apply only to internships, not papers. Preserve existing search paths.
5. Test extraction/evidence boundaries, SSRF/robots, deduplication/targets/deadlines,
   auth/stream contract, frontend states, and the Docker/browser integration.
6. Update generated OpenAPI, roadmap/spec and learning log; review diff and rebuild.

## Limits
First version: request-scoped scans capped at 120 seconds, 40 pages, depth 3,
2 MB per response, and one in-flight scan per user with bounded server concurrency.
No durable scan jobs or automatic outreach. Discovery is lexical matching, not a
measured semantic ranker. Auth still depends on the owner's reachable Supabase
project. Missing access or fewer matching papers is a partial result, not success
filled with unrelated records. API-first remains available; direct scraping is an
explicitly user-approved alternative to the prior API-first-only ordering.

## Implementation status — 2026-10-09
- Implemented request contracts, reviewed source registry, HTML extraction,
  robots-aware public-IP-pinned fetching, bounded streaming and the Discover UI.
- Corrected stale KAUST/ISTA directory links after live checks. Added the official
  ISTA Lampert lab entry point because some directory publication lists are
  embedded third-party content. This is limited coverage, not an exhaustive index.
- Fixed a live-discovered queue starvation bug: a bounded priority queue now
  replaces low-priority pending links when a useful publication link arrives.
- Automated checks: Ruff, mypy, all 124 backend tests (28 university tests),
  frontend lint/typecheck, all 56 frontend tests, and all 10 Chrome browser tests
  passed. Production Next build and both Docker image builds passed. OpenAPI
  export and generated client checks passed. Diff whitespace check passed.
- Real Supabase sign-in remains blocked: the configured project hostname still
  does not resolve. Browser tests use the isolated test identity and the scan UI
  test uses a documented stream fixture; live crawler checks are separate.
- Live machine-learning scan reached 20 unique citations in 22 seconds, from
  official ISTA pages. IITGN returned HTTP 403; some KAUST paths disallowed bots.
  These conditions are reported, not bypassed. Program evidence was retrieved
  separately from OIST, KAUST and ISTA; work mode remained unknown.

- Docker runtime verification complete: four healthy services; web/API/proxy 200;
  anonymous scan 401; production-container crawler found 10 ISTA citations in
  10 seconds across five pages. Feature implementation/testing is complete;
  a real-account sign-in walkthrough awaits Supabase project reachability.
