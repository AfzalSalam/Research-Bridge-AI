# Professor public-email discovery — approved 2026-10-10

## Goal
Complete the gap between paper-backed researcher discovery and outreach: find a
public professional email on a matching official profile, show evidence and its
check date, and let the student copy it. Never infer an address or send messages.

## Implementation sequence
1. Build a server-owned author identity from stored papers, ORCID and historical
   affiliations. Add a bounded contact lookup using the existing reviewed HTTPS
   university registry, DNS-pinned fetcher, robots controls and shared pacing.
2. Locate likely profiles by name from relevant official directories; allow an
   optional official profile URL within reviewed hosts. Extract mailto, plain and
   explicitly obfuscated public addresses. Require a personal profile/name plus
   corroborating ORCID or publication evidence before offering a matched email.
   Ambiguous profiles remain review links, not guessed recipients. Generic office,
   support, and other people's addresses must not be attributed to the author.
3. Persist structured public contact evidence and source timestamps with an
   Alembic migration. Cache recent lookups; allow explicit recheck. Apply account
   authentication, process concurrency bounds and request/time/page limits.
4. Add an accessible Find public email panel next to the selected researcher's
   outreach area: progress, cancel, source links, evidence, copy, not-found,
   unsupported-source, ambiguous and partial-failure states. Preserve tab results.
5. Test extraction/identity false positives, crawl/auth boundaries, cache behavior,
   frontend states and a browser flow. Run project quality gates, live smoke,
   update learning log/spec/README, rebuild local Docker and verify health.

## Scope and limits
The approved extension adds registry-verified institutions to reviewed sources; arbitrary user domains are still rejected.
Directory discovery may miss profiles; the optional reviewed profile URL is a
fallback. No paid search service or new dependency. No SMTP probing, no email
pattern guessing, no mass lookup/sending, no assertion of inbox deliverability.
Researcher role and internship availability remain separate unknown facts.
Public page content is untrusted data, never instructions to an LLM. Historical
institution alone is insufficient to confirm a namesake's contact. Stored contact
evidence is public catalog data, not a student's private draft/profile.

## Acceptance
A selected author can be looked up end-to-end, with an evidenced public email or
an honest bounded failure. A wrong-person or generic address is never shown as a
confirmed recipient. Navigation retains results; refresh marks unfinished work
interrupted. Tests and live observations distinguish fixtures from real sources.


## Scope extension approved by user — 2026-10-10
Remove the hard-coded seven-university ceiling. Use institution identifiers from
paper metadata to resolve official websites through a trusted institution
registry (ROR/OpenAlex), then build a per-lookup allowlist. Do not trust arbitrary
URLs, broad .edu suffixes, or every hyperlink as official. Preserve DNS/public-IP,
HTTPS, redirect, robots, page/time and concurrency controls.

Prioritize relevant institutions rather than attempting to crawl every university
for each search. Separate paper-backed researchers open to an enquiry (availability
unknown) from evidence-confirmed internship programs. Confirmed programs need an
official call, eligibility/current dates and explicit work-mode evidence; no global
internship coverage or active-opening claim follows from institutional membership.

Sequence: finish existing email release checks; implement trusted official-domain
resolution and targeted directory/profile crawling beyond the seed list; expand
opportunity-source discovery with verified status, provenance and partial-coverage
reporting. No paid provider, guessed emails or unrestricted crawler introduced.


Implementation and local Docker rollout are complete. Backend 153 tests, frontend 64 tests and 13 browser tests passed; lint/type checks, API contracts, production builds and health/auth smoke checks passed.
Live ROR resolution returned MIT and its official domains. This verifies domain discovery, not internship availability.
