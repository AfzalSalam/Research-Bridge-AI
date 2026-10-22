# Gmail development setup

Status: preparation guide; Gmail connection and sending are not implemented yet.
Supabase sign-in does not grant Gmail access. Keep using it for the app account.

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. In APIs & Services, enable Gmail API. Enable Cloud Pub/Sub for the later reply-sync phase.
3. Configure Google Auth Platform branding, support email, audience and developer contact.
   Use External / Testing for development and add only consenting test accounts.
4. Configure these scopes: `https://www.googleapis.com/auth/gmail.send` and
   `https://www.googleapis.com/auth/gmail.readonly`. Read-only permission covers the
   mailbox broadly; the application will limit stored message content to tracked conversations.
5. Create an OAuth client of type Web application. The exact backend callback URL
   will be documented alongside the implemented connection endpoint in phase 3.
   Register that exact URL, including scheme, port and path; do not substitute
   the Supabase sign-in callback. Use a separate HTTPS client for production.
6. Keep the client secret in backend-only environment configuration. Never paste it
   into a chat, commit it, or put it in a NEXT_PUBLIC variable. Encrypted token
   storage also needs a separately managed encryption key, backed up securely.
7. For reply sync, create a Pub/Sub topic in the same Google Cloud project used
   for Gmail watch requests. Grant topic publisher access to
   `gmail-api-push@system.gserviceaccount.com`. Configure authenticated push delivery
   to the public HTTPS backend endpoint once phase 4 defines it; configure the
   expected JWT audience and service-account identity explicitly.
8. Use two dedicated consenting mailboxes to test connect, reviewed send, reply,
   offline synchronization, disconnect and reconnect. No real professor outreach
   is needed to test the integration.

The app must renew watches daily and reconcile periodically: notifications can be
missed. Development OAuth consent may require reconnecting as testing refresh
credentials expire. Keep production publication separate from local testing.

Public release requires privacy/consent/deletion pages, verified domains, Google
OAuth verification, and any required restricted-scope security assessment.
Gmail read-only is restricted; sending is sensitive. Do not mark public launch
ready merely because the test-account flow works.

Official references:
- [Web-server OAuth setup](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Gmail scope requirements](https://developers.google.com/workspace/gmail/api/auth/scopes)
- [Push notifications and watch renewal](https://developers.google.com/workspace/gmail/api/guides/push)
- [Restricted-scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification)
