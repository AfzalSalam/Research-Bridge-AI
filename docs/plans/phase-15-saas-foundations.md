# Phase 15 - SaaS Foundations & Real Authentication

## Objective
Migrate the Research Bridge AI application from a recruiter portfolio demo into a secure, multi-tenant SaaS. This involves removing all mock authentication bypasses, requiring live Supabase JWT tokens, and establishing fundamental user onboarding capabilities.

## Requirements
1. **Remove Bypasses:** The frontend and backend must strictly enforce authentication. The demo_mode flags must be stripped entirely.
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
- *Note:* UI design should be kept strictly functional during this phase. Polish will be applied in Phase 18.

## Verification
- Run the full test suite (uv run pytest) to ensure database repositories handle owner_id scoping correctly.
- Manually create an account on the live Supabase project and verify that login succeeds.
- Verify that attempting to access /api/v1/outreach/drafts without a token returns a 401 Unauthorized.
