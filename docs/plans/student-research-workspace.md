# Student research workspace — approved 2026-10-09

## Scope and sequence
One approved usability phase: preserve discovery across navigation, simplify the
student journey, group known coauthors by shared paper, and automatically scan a
larger reviewed university registry. No all-university coverage claim.

1. Add account-scoped research state in the existing TanStack Query provider.
   Keep in-flight requests alive during route changes; abort on account change,
   explicit cancel/clear, or browser closure. Restore validated completed/partial
   results and inputs after reload from this tab's session storage. A refreshed
   in-flight scan becomes interrupted, never a falsely running or complete scan.
   No credentials or raw resume uploads are persisted in this snapshot. Search
   responses can contain profile-derived matching facts and guided draft text;
   snapshots are account-scoped, tab-local, and removed on account switch/sign-out.
2. Simplify Discover into website or academic-database search, with the guided
   email workflow in a clearly labelled optional section. Rename Mentors in
   navigation to Find Professors but label unverified people as research authors.
3. Group returned researcher candidates by stable supporting-paper IDs. Show
   source links, publication-time affiliations and individual selection for
   outreach; do not invent author roles, contacts or complete coauthor coverage.
4. Remove mandatory institution selection. Add India/International/Both region
   choice and a read-only source list. Verify added official program/research
   entry points, retain allowlists, robots/SSRF controls and the 120-second budget.
   Display elapsed seconds, paper/page counts and the maximum scan time, not a
   fabricated estimated time remaining.
5. Verify navigation/reload/in-flight cancellation/account isolation, source
   selection and coauthor grouping. Run required checks and browser tests,
   update learning log and rebuild Docker. Preserve existing unrelated changes.

## Limits
Session storage is per browser tab, not cross-device saved search history.
Refresh stops active network work; received evidence remains. Scraped citations
without author metadata do not get guessed author groups. Registry breadth and
lexical matching do not establish an internship vacancy or nationality preference.
No new dependencies or distributed workers are needed.


## Implementation status — 2026-10-10
Implemented shared query state, validated tab snapshots, navigation-safe requests,
student-facing labels, coauthor groups, regional automatic source selection and
elapsed/count/budget progress. Registry now includes seven reviewed institutions.
No new dependencies or schema migration in this usability phase.

Live registry smoke: machine learning, target 10, all regions: 10 citations in
26 seconds, 15 pages read / 18 attempted. IISc was correctly closed; IITGN HTTP
403 and EPFL research-host robots verification limits remained visible. This
single query is not a retrieval-quality benchmark or proof of source diversity.
Final validation and Docker rollout results are recorded in docs/LEARNING_LOG.md.

Completed: frontend lint/typecheck/contracts/build, 61 frontend tests, 12 browser
tests, backend lint/mypy and 125 backend tests passed. Docker rebuilt and started;
all four services healthy, HTTP health checks 200 and anonymous scan 401.
