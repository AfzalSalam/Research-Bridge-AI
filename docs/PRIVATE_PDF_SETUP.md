# Private PDF reading: setup and implementation status

Phase 2 is in progress. Private storage, workers and authenticated document APIs
are implemented. The paper workspace includes upload/status/removal controls and
numbered extracted-text previews. Uploads remain disabled by default pending live
Storage/scanner validation. Original PDF viewing and cited Q&A remain outstanding.

## Supabase preparation

Use the same project as account sign-in. In Storage create a bucket named
`research-documents` with Public disabled, PDF MIME type only, and a 20 MB object
limit. Do not grant anonymous access or general authenticated read/list access.
The backend will authorize owner access and later issue short-lived links only
for scanned, ready documents. Quarantine objects must never receive preview links.
Keep storage credentials in backend-only configuration, never NEXT_PUBLIC values,
Git or chat. The backend settings are listed below.
Do not change existing authentication settings to prepare Storage.

## Antivirus preparation

The processing interface speaks ClamAV's INSTREAM protocol (default port 3310).
Use a maintained ClamAV daemon with fresh signatures and a stream size limit of
at least 20 MB. Keep its port on the private application network; never expose it
to the public internet. It must explicitly return a clean result before parsing.
Timeouts, malformed responses, limit errors and unavailable scanning fail closed.
No scanner service has been added to Compose yet; its configuration will accompany
the durable worker. There is no bypass flag for development uploads.

## Processing rules already implemented

- Maximum 20 MiB / 100 pages; encrypted and textless PDFs are unsupported.
- Reject active actions and embedded attachments, even after a clean scan.
- Extract numbered pages and chunks with exact character offsets within each page.
- Empty pages are reported as text gaps; no OCR or inferred content.
- Run parsing in a separate process with a 30-second wall timeout.
- Linux adds 20-second CPU and 768 MiB virtual-memory limits; Windows uses the wall
  timeout only. Production processing must use the Linux worker/container.
- Cap extracted text at 20,000 characters/page and 500,000/document. Complex files
  can be unsupported even if their uploaded byte size is below 20 MB.
- Never include PDF text in parser error logs. No content reaches an AI provider.

## Verification

From apps/api: `uv run pytest tests/test_pdf_processing.py -q`.
Fixtures test valid text, source offsets, page/byte limits, encryption, active
content, scanner failures/protocol replies, subprocess success and cancellation.
Protocol tests use a local fixture server, not a real antivirus signature database.
Real scanner and Supabase validation remain outstanding. Extraction does not
preserve all layout, equations, tables or column order; citation evaluation remains
required before paper Q&A is advertised.

References:
- [Supabase private buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals)
- [ClamAV scanning](https://docs.clamav.net/manual/Usage/Scanning.html)
- [pypdf extraction limitations](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)


## Database processing foundation (2026-10-12)
Migration 20261012_0007 now stores owner-scoped documents, pages/chunks and jobs.
Processing claims expire after five minutes and use unique tokens to prevent an
expired worker from publishing results. A job permits at most three attempts.
The worker below now uses these claims. This does not enable upload/preview;
authorized endpoints and the reading UI remain pending.


## Storage and worker configuration (2026-10-15)
Set these in apps/api/.env on the server only:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_STORAGE_SERVICE_KEY=YOUR_SERVER_STORAGE_CREDENTIAL
DOCUMENT_STORAGE_BUCKET=research-documents
DOCUMENT_SCANNER_HOST=YOUR_PRIVATE_CLAMAV_HOST
DOCUMENT_SCANNER_PORT=3310
```

Use a server credential authorized to read bucket settings and upload/download/delete
objects. Do not put real credentials in .env.example, Git, browser settings or chat.
The adapter verifies the bucket is private before upload/download, does not follow
redirects, uses UUID-only paths, caps response sizes, and refuses unconfigured use.
Deletion still works if an administrator accidentally changes bucket visibility.
Do not make the bucket public or grant general read/list policies.

After applying migrations, inspect aggregate state from apps/api:
`uv run python -m app.documents.worker --status`.
Process at most one cleanup and one PDF job with:
`uv run python -m app.documents.worker --once`.
Omit --once for the continuous loop. Production must run the Linux image to enforce
parser CPU/memory limits, for example after `docker compose build api` and normal
startup: `docker compose run --rm --no-deps api python -m app.documents.worker`.
This command is a foreground worker; use a supervised service in deployment.
No worker/scanner is automatically started by the default Compose configuration.

Upload service limits: 100 document records and 200 MiB per owner; each PDF remains
limited to 20 MiB. Upload intent and an independent cleanup ledger commit before
external storage writes. A timed-out upload is never assumed safe or readable.
Objects use owner UUID/document UUID paths; original filenames are not object keys.

Migration 20261012_0008 adds the cleanup ledger, intentionally without cascading
foreign keys. Account deletion removes access/content records immediately; the
ledger retains only UUIDs, bucket and retry metadata until object removal succeeds.
There is a 15-minute upload grace window. Abandoned uploads and terminally rejected
files become eligible for cleanup. Processing/ready documents are retained.
Cleanup has five-minute fenced claims, exponential retry delay and at most ten
attempts. Failed cleanup records remain visible under --status; investigate and
reset only the affected record after fixing Storage. Do not delete the ledger to
hide an error. Physical deletion requires a running worker and available Storage.

Tests use fake Storage transport and a fixture scanner; these are not live-service
validation. Full source references for the transport contract:
https://github.com/supabase/storage-py/blob/main/storage3/_async/file_api.py


## Authenticated interface (2026-10-15)
The paper workspace now displays private document status, upload/removal controls,
and a numbered extracted-text preview. This is not the original PDF layout viewer
or cited Q&A. Uploaded paper identity is student-provided, not automatically verified.
DOCUMENT_UPLOADS_ENABLED=false is the default. Set it true only after validating
private bucket policies, real antivirus and a continuously running worker. The API
also requires a Supabase URL/key and scanner host before accepting files.

Authenticated routes: GET/POST /api/v1/documents/paper/{paper_id};
GET/DELETE /api/v1/documents/{document_id}; GET /api/v1/documents/{document_id}/pages.
POST uses raw application/pdf bytes and a filename query parameter, limited to
20 MiB and 30 seconds to receive the body. HTTP 202 means queued, not scanned.
The service limits each owner to five persisted upload attempts per minute,
in addition to document/storage quotas. Ready-only page responses use private,
no-store caching headers. Listing/removal work when new uploads are disabled.
Removal queues physical cleanup; it does not promise immediate Storage erasure.

The UI polls pending statuses every three seconds while mounted. Navigation does
not stop the separate worker. Status survives refresh/restart in database records.
Unsupported/rejected files cannot be opened for text reading.


### Original PDF reader integration (2026-10-15)
Ready PDFs now offer an explicit original-file viewer and download fallback alongside
extracted text. Bearer-authenticated fetch uses no-store; temporary blob URLs are
revoked on close/unmount, pending fetches abort, and query bytes expire immediately
after the reader unmounts. Account identity changes already remount the private
workspace. No dependency or migration added. Browser-native PDF support varies;
the sandboxed preview may require using the download fallback. Live uploads remain
disabled pending Storage/ClamAV validation. Cited Q&A and OA fetching remain pending.
