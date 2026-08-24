# Phase 10 — Authentication, privacy, and security

**Status:** In progress — Supabase Auth selected

## 1. Outcome

Replace the shared server-configured demo owner for live data with a verified,
per-request identity. A signed-in student can access only their own profile,
saved items, outreach drafts, applications, and future private uploads. The
fictional recruiter demo remains public, separate, and visibly fictional.

This phase establishes security boundaries; it does not add ranking, scraping,
automatic email, resume parsing, or a production deployment.

## 2. Current-state audit

### Reusable foundations

- `account_owners` already distinguishes `demo` from `authenticated` owners and
  has a unique `auth_subject` column.
- Profile, saved-item, outreach-draft, application, and event records already
  reference an owner with database foreign keys and appropriate cascades.
- Repositories accept an `owner_id`, so the service boundary can retain its
  current shape after identity is derived from a request.
- FastAPI already centralizes configuration, structured errors, request IDs,
  CORS, transaction rollback, and external HTTP lifecycle handling.
- Next.js already proxies browser API calls through same-origin `/backend`, so
  the browser need not know the FastAPI origin.
- Existing E2E uses owned loopback fixtures and SQLite, so two-user isolation
  can be tested without a paid identity-provider account.

### Security gaps to close

- `DEMO_OWNER_ID` is injected into live profile, outreach, opportunity, and
  application services. Every browser therefore reads or writes the same data.
- No browser sign-in state, server-side token verification, protected-route
  policy, or authenticated response contract exists.
- CORS does not yet allow `Authorization`; a bearer token must be forwarded only
  when the API is called by the signed-in browser.
- No upload route, object-storage abstraction, deletion route, user rate limit,
  or security-event schema exists. Those are designed before exposure.
- The public health and fictional-demo endpoints must remain intentional public
  exceptions; every private route must become deny-by-default.

## 3. Decision: authentication provider

### Selected provider — Supabase Auth

Use **Supabase Auth** for the placement release, with email/password first and
Google sign-in only after the core isolation tests pass. The browser uses the
official Supabase JavaScript client for session handling; FastAPI independently
verifies each access token against the project's JWKS. FastAPI remains the
authorization authority: a valid token identifies a subject but never grants
database-row access.

Why this fits the modular monolith:

- It preserves the existing PostgreSQL and SQLAlchemy database rather than
  requiring a data migration to Supabase.
- It avoids building password storage, recovery, OAuth callbacks, session
  rotation, and signing keys from scratch.
- Its stable `sub` claim maps directly onto `AccountOwner.auth_subject`.
- It gives a recruiter an explainable flow: Next.js obtains a session token;
  FastAPI validates it; repositories enforce the owner filter.

Supabase documents browser-managed access tokens and a project JWKS endpoint for
asymmetric-token verification. [Supabase JWT documentation](https://supabase.com/docs/guides/auth/jwts)
is the source of truth for the implementation.

### Alternatives

| Option | Decision | Reason |
| --- | --- | --- |
| Hand-built email/password + JWT | Reject | It adds password reset, credential storage, OAuth, session revocation, email delivery, and key-rotation risk without product value. |
| Next-only session checks | Reject | FastAPI owns private database operations, so backend verification is mandatory. |
| Clerk | Viable alternative | It has polished hosted UI, but the user selected Supabase Auth for this project. |

### User decision required before implementation

1. Create/select a Supabase project and enable Email/Password authentication.
2. Put `NEXT_PUBLIC_SUPABASE_URL` and the project publishable/anon key in
   `apps/web/.env.local`; put `SUPABASE_URL` and expected JWT audience in
   `apps/api/.env`. Never place a Supabase service-role key in the browser or
   paste secrets into chat, code, or committed files.
3. Google sign-in remains deferred until Email/Password and isolation tests pass.

## 4. Trust boundaries and data flow

```text
Browser
  -> Supabase Auth UI / session state
  -> same-origin Next.js /backend request with short-lived bearer token
  -> FastAPI authentication dependency
      -> validates issuer, audience, expiry, signature, and token type
      -> extracts immutable provider subject (sub)
      -> AccountOwnerRepository.get_or_create_authenticated(sub)
      -> AuthenticatedPrincipal(owner_id, subject)
  -> service receives owner_id from principal, never request body
  -> repository queries/mutates only WHERE owner_id = principal.owner_id
  -> PostgreSQL private rows

Public exceptions: /health and fictional /demo routes only
```

The browser may select one of its own records, but it never sends an owner ID or
subject as authority. UUIDs are opaque identifiers, not authorization controls.

## 5. Route policy

| Route group | Access | Enforcement |
| --- | --- | --- |
| `GET /health` | Public | No identity required; no private diagnostics. |
| `/demo/*` | Public | Fictional-only responses; never private data. |
| `/discovery/*`, mentors, opportunity search | Public initially | Strict validation, shared IP rate limit, no persistence until authenticated save. |
| `/profile`, outreach drafts, saved opportunities, applications | Authenticated | Shared FastAPI `current_principal`; owner-scope every repository query. |
| Future private files, deletion, exports | Authenticated + owner-scoped | Explicit object ownership plus user-level rate limits. |
| Administrative maintenance | No browser route | Deployment/service credentials only. |

Changing a route from public to private must update its FastAPI dependency and
OpenAPI contract; a frontend redirect is never authorization.

## 6. Database and deletion design

Create one Phase 10 Alembic revision that retains existing owner IDs and foreign
keys, adds a portable authenticated-subject index only if necessary, and does
not copy the shared demo owner's records into a real account. Demo stays demo;
signed-in accounts start with an empty private workspace.

`DELETE /api/v1/account` requires a fresh authenticated request and explicit UI
confirmation. It deletes the owner aggregate so profile, saves, drafts,
revisions, applications, and events cascade. It also removes owned private
objects by generated object key. Public academic catalog and public-source
provenance remain. No legal retention or external-provider deletion promise is
claimed before deployment requirements are known.

## 7. Private upload scope — separate approval

Resume upload is not required for authentication. If separately approved, the
first slice supports only one private PDF, with: authenticated owner before
bytes; 5 MiB size limit; PDF MIME **and** signature allowlist; generated object
key; no client path; no public URL or inline render; storage outside webroot;
owner-scoped attachment-only download; and upload/download/delete rate limits.
No request-path text extraction or LLM processing is included.

This follows OWASP guidance on allowlists, generated filenames, size limits,
authorization, and storage outside the webroot. [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

## 8. Threat model

| Threat | Mitigation | Required test |
| --- | --- | --- |
| Forged, expired, wrong-issuer, or wrong-audience token | Backend signature/claim verification; fail closed with 401 | Invalid-token matrix returns 401 without owner creation. |
| IDOR / UUID swapping | Principal-derived owner ID in every repository lookup/mutation | User A cannot read/update/delete User B records. |
| Shared demo data leak | Public demo uses only `kind=demo`; private dependencies never fall back | Anonymous caller cannot read private data; signed-in caller cannot mutate demo. |
| Token leakage | Same-origin proxy, secret env only, restrictive CORS/headers, no token logs | Logs/error bodies contain no token pattern; unknown origin is rejected. |
| Credential stuffing / expensive abuse | Provider controls plus app IP/user quotas on costly routes | 429 uses structured safe response and retry metadata. |
| SSRF / hostile URL | Existing fixed-origin/allowlist policy remains; files never trigger remote fetch | Arbitrary URL never reaches outbound client. |
| Malicious resume | Narrow PDF validation, generated key, attachment-only download, no parsing | Spoofed MIME, oversize, path-like name, wrong signature rejected. |
| Privacy disclosure | Minimal response fields, owner filters, deletion, audit-safe logs | Public/demo snapshots reject private fields. |
| Cross-site private write | Consistent bearer-token or cookie/CSRF policy, documented before code | Cross-origin write rejected. |

OWASP recommends deny-by-default authorization and two-user object-level tests,
not reliance on unguessable identifiers. See [Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
and [IDOR testing guidance](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html).

## 9. Implementation sequence

1. Add provider configuration validation, auth runtime, typed principal, safe
   401/403 contracts, and generated test token/JWKS fixtures.
2. Replace `demo_owner_id` injection in private-service dependencies with the
   principal owner. Public demo services remain unchanged.
3. Add Supabase Auth UI, protected-route behavior, client bearer-token injection, and
   loading/error/expired-session states.
4. Add the migration and two-principal tests for profile, outreach, saves, and
   applications.
5. Add account deletion confirmation, cascade validation, and E2E coverage.
6. Add a bounded in-process IP/user limiter and security headers. Document that
   distributed enforcement is deferred until deployment warrants it.
7. Only after separate approval, implement the private-PDF adapter and complete
   upload threat testing.
8. Regenerate contracts; run backend, frontend, migration, security, and E2E
   gates; update learning log; review and commit.

## 10. Acceptance criteria

- FastAPI verifies every private request server-side and denies missing/invalid
  identity by default.
- Owner A cannot access owner B data through any route or object identifier.
- Public demo works without credentials and cannot expose private data.
- Existing live/demo contracts still work after authentication.
- Account deletion removes the private aggregate and owned objects with clear
  documentation of retained public data.
- CORS, headers, limits, secrets handling, and safe logs have automated tests.
- Any upload feature meets section 7 completely; otherwise it is deferred.

## 11. Quality gates

```powershell
Set-Location apps/api
uv run ruff check .
uv run mypy app
uv run pytest
uv run alembic upgrade head
uv run alembic check

Set-Location ../..
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
npm.cmd audit --omit=dev --audit-level=high
```

Run the migration cycle against isolated PostgreSQL, test anonymous/user A/user
B identities, and inspect output for token or profile-content leakage.

## 12. Non-goals and limitations

- Passwords, recovery, OAuth callbacks, and session signing are provider-owned.
- No authorization is delegated to an LLM, frontend check, or UUID randomness.
- No antivirus guarantee, resume parser, public file link, or background scan is
  claimed in the first upload slice.
- An in-process limiter is placement-release only; it cannot coordinate API
  replicas. Redis remains deferred.
- This plan is not a substitute for a penetration test, legal privacy review, or
  provider DPA review.

## 13. Exact next step

Create the Supabase development project and configure its public URL/key outside
version control. Then implement steps 1–4 as the first Phase 10 slice; Google
sign-in and private uploads remain separate explicit approvals.
