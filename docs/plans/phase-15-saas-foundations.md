# Phase 15 - SaaS Foundations & Real Authentication

## Current execution slice — 2026-10-07

Status: This slice is implemented and passes automated verification; ready for review.
The prior completion claims are not a live release verification.

Verification: frontend lint/typecheck, 50 unit tests, API contract consistency,
and the production build passed. All 9 Playwright journeys passed (including
axe checks, mobile layout, onboarding, matching, draft review, and tracking).
Backend Ruff and mypy passed; pytest passed all 96 tests using a fresh local
temporary directory. Live Supabase and PostgreSQL checkpoint smoke tests remain
open; this does not complete the entire SaaS phase.

### Scope and acceptance criteria

1. Replace the authenticated profile page's demo persistence with the existing
   account-profile API. Preserve the approved layout and design tokens; correct
   obsolete demo labels. Reuse the validated form contract for onboarding/editing.
2. Scope profile query state to the signed-in identity, distinguish a missing
   profile from an API failure, and reset dependent result/draft state after edits.
3. Make mentor discovery and the guided workflow read the authenticated account
   profile. Missing profiles must produce a structured error, not fictional facts.
4. Check workflow ownership before resuming or streaming stored state. Another
   user's workflow must never be read, changed, or executed.
5. Add regression coverage for two-account profile isolation, personalized mentor
   inputs, profile save/reload, and workflow access. Update obsolete browser tests
   to exercise the current authenticated UI using isolated test auth/provider data.
6. Run frontend lint, typecheck, unit tests and build; backend Ruff, mypy and pytest;
   API contract checks and the Playwright critical journey when the environment
   permits. Record actual results and remaining limitations.
7. Update the learning log and roadmap status, inspect the full diff, and leave
   the phase reviewable. Do not claim the whole SaaS or deployment is complete.

No new application dependencies or database schema changes are expected. Billing,
new data providers, ranking experiments, and a visual redesign are outside this
slice. Existing labelled sample/demo endpoints remain separate from real accounts.

## Objective
### Transfer to the owner's main checkout — 2026-10-07

The owner requested that these changes be transferred into
`C:/Users/afzal/Desktop/Research-Bridge AI`. Compare each changed file against
the common Git base and the destination, abort on conflicting edits, back up
affected destination files, and copy only the reviewed source/tests/docs changes.
Preserve environment files, dependencies, database volumes, and unrelated work.
Verify destination content against the tested source and run focused checks from
the Desktop checkout. This transfer does not establish Docker or live-service
readiness.

Migrate the Research Bridge AI application from a recruiter portfolio demo into a secure, multi-tenant SaaS. This involves removing all mock authentication bypasses, requiring live Supabase JWT tokens, and establishing fundamental user onboarding capabilities.

## Requirements
1. **Remove Production Bypasses:** Deployed authenticated flows must enforce authentication. Explicitly isolated test identities and labelled sample endpoints may remain for reproducible testing; they must not substitute fictional facts in real accounts.
2. **Real Authentication:** Require the user to configure a live Supabase project. The backend must be able to securely verify tokens using the Supabase JWKS endpoint.
3. **Data Isolation (Multi-tenancy):** Every database read/write operation must be strictly scoped to the owner_id derived from the verified JWT token.
4. **User Onboarding Flow:** When a user first signs in via Supabase and lands on the frontend, a new database record must be created, and the user should be prompted to fill out basic profile information (name, major, interests) if it's missing.

## Implementation Steps
### 1. Revert Demo Modifications
- Update pps/web/src/features/auth/login-form.tsx to remove the 'View Demo' bypass button.
- Update pps/web/src/features/auth/use-auth.ts to remove the mock user injection.
- Update compose.yaml to ensure the API environment uses production-grade JWT validation rather than the e2e static token override.

### 2. User Profile Onboarding (API)
- Add a new endpoint to handle first-time profile creation or syncing immediately after login.
- Ensure the AccountOwner and StudentProfileRecord are appropriately created.

### 3. User Profile Onboarding (Web)
- Create an onboarding modal/page that forces new users to complete their profile before accessing the main dashboard.
- *Note:* UI changes in this phase are limited to functional correctness. The
  current roadmap reserves broader UI work for Phase 16.

## Verification
- Run the full test suite (uv run pytest) to ensure database repositories handle owner_id scoping correctly.
- Manually create an account on the live Supabase project and verify that login succeeds.
- Verify that attempting to access /api/v1/outreach/drafts without a token returns a 401 Unauthorized.


Transfer status: Completed and verified in the Desktop checkout on 2026-10-07.
Frontend checks and 50 tests passed; backend checks and 9 focused tests passed.
See the learning log for backup location, preserved local edits, and limitations.


## Docker startup repair — 2026-10-07

Authorized scope: restore one-command local Docker startup in the Desktop checkout.
Use the workspace root lockfile and Node 24 for the frontend image, mount the
existing frontend environment as a build secret, load backend runtime environment,
and use the installed Python virtual environment consistently. Exclude credentials,
private files, caches, and host dependencies from build contexts. Bind PostgreSQL
on localhost:5433 to avoid the independently installed Windows server on 5432.
Preserve database volumes and all existing credentials. Build and start services,
verify HTTP health through both API and web proxy, check PostgreSQL checkpoints
and anonymous auth rejection, and inspect Supabase JWKS availability without
creating accounts or sending emails. Document actual results and remaining live
account checks; update startup examples. No new application dependencies.


Docker slice outcome: both images built; all four services healthy; HTTP and
Chrome anonymous-user smoke checks passed. Existing database marker repaired
only after a full backup and zero-difference schema comparison. Supabase project
DNS fails on host and container; actual login requires owner dashboard follow-up.
See the learning log for exact backup location and verification details.


## Login/profile repair (2026-10-10)
Investigate observed authenticated profile 401s. Add safe verification diagnostics (no tokens or private claims), reproduce with the existing browser session, repair the confirmed cause without weakening validation, add regression coverage and redeploy. Preserve account data.

Diagnosis: signed token rejected with ImmatureSignatureError; Windows/container clock is roughly 13.5 hours behind provider. Windows time service is stopped and cannot be started from this process. Await owner automatic-time synchronization, then retry live profile. No auth relaxation or profile data changes.


2026-10-11 live verification: after the owner synchronized Windows time, the provider/container clock difference fell to approximately 33 seconds. The existing signed-in browser successfully loaded /profile with the saved form and Profile is up to date. No profile edits or authentication relaxation were needed. The login/profile incident is resolved.
