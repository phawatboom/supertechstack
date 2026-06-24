# Authentication fixes

This document explains the authentication and workspace-creation changes made
to the web application. It is written as a review reference rather than an
implementation guide.

## Current implementation summary

The final implementation includes:

- Supabase email/password authentication;
- authenticated API requests using Supabase access tokens;
- one shared token refresh for concurrent 401 responses;
- protection against duplicate Supabase session updates;
- a signed-out workspace draft that resumes after authentication;
- idempotent workspace creation to prevent duplicate database rows;
- JWT clock-skew tolerance in the API;
- a public demo workspace with limited anonymous access;
- Webpack for local Next.js development because Turbopack intermittently
  omitted the dynamic workspace route from its development manifest.

## What users should experience

### Creating a workspace while signed out

The public homepage always shows the workspace creation form.

When a signed-out user enters a workspace name and clicks **Create workspace**:

1. The browser saves the unfinished workspace locally.
2. The user is redirected to the **Create account** tab.
3. The user creates an account or signs in.
4. After Supabase confirms the session, the homepage creates the saved
   workspace through the authenticated API.
5. The browser opens the newly created workspace.

The saved draft expires after 24 hours. It contains the workspace name,
description, and a random request ID. It does not contain credentials, access
tokens, refresh tokens, or uploaded files.

Each draft also has a random creation request ID. The frontend sends it as an
`Idempotency-Key` header. The API stores that key with the workspace and has a
database uniqueness rule for each owner. If React, the browser, or the network
replays the same POST, the API returns the already-created workspace instead of
inserting another row.

Relevant files:

- `web/app/page.tsx`
- `web/app/auth/page.tsx`
- `web/app/lib/pending-workspace.ts`
- `api/app/routes/workspaces.py`
- `api/app/models/workspace.py`
- `api/migrations/alembic/versions/0003_add_workspace_creation_key.py`

### Why duplicate workspaces appeared

The original post-auth flow ran workspace creation from a React effect. React
development remounts, authentication events, navigation, and request retries
can replay asynchronous work. The browser-side `useRef` and local-storage
cleanup reduced that risk but could not guarantee that a POST reached the API
only once.

The API previously treated every POST as a new command and always inserted a
row. Therefore three deliveries of one logical request produced three
workspaces.

The idempotency key fixes this at the correct boundary: the database. Existing
duplicate rows are not deleted automatically because identical names do not
prove that the workspaces are accidental duplicates. They should be reviewed
and deleted manually.

Migration `0003_add_workspace_creation_key.py` must be applied before using the
updated workspace creation endpoint:

```bash
cd apps/api
alembic upgrade head
```

### Signing in and loading private data

Supabase stores the browser session and issues an access token. The frontend
sends that token to the Railway API in this header:

```text
Authorization: Bearer SUPABASE_ACCESS_TOKEN
```

Railway validates the token using the Supabase JWKS endpoint. The verified
token subject (`sub`) becomes the workspace owner ID.

Relevant files:

- `web/app/components/auth-provider.tsx`
- `web/app/lib/api.ts`
- `api/app/security.py`

## Why production showed both 401 and 200

Several workspace requests can begin at nearly the same time. For example, a
workspace page loads its workspace, sources, chunks, answer traces, and answer
settings concurrently.

If an access token is close to expiration, those requests can all receive
`401 Unauthorized`.

Previously, each failed request independently did this:

1. Refresh the Supabase session.
2. Retry its request.
3. Sign the browser out if the retry still returned 401.

That behavior created a race. One request could successfully refresh the
session while another request was still retrying with different token state.
The second request could then sign out an otherwise valid user.

This explains production logs containing a temporary 401 followed by a 200.
The first request used invalid or outdated authentication state; the later
request used the refreshed token.

The initial session-loading race suggested in the external diagnosis was not
the main issue here. `AuthProvider` already displayed a loading screen while
Supabase restored the initial browser session.

## Fix: one shared token refresh

`web/app/lib/api.ts` now keeps one in-progress refresh promise.

When several requests receive 401 simultaneously:

1. The first request starts `refreshSession()`.
2. Other requests wait for the same refresh operation.
3. They retry using the same new access token.

This is sometimes called a single-flight operation. It prevents multiple
requests from rotating the refresh token independently.

The API helper also no longer signs the user out simply because a request
returned 401 twice. A 401 can mean:

- the API received a token slightly too early because clocks differ;
- a deployment briefly used inconsistent configuration;
- the token was refreshed concurrently;
- the backend rejected a valid-looking token for another reason.

Supabase remains responsible for reporting an actual `SIGNED_OUT` event.
Removing the automatic logout prevents a temporary backend failure from
destroying a valid browser session.

## Fix: ignore duplicate session events

Supabase can report the stored session through both:

- the initial `getSession()` call;
- the authentication state listener.

`web/app/components/auth-provider.tsx` now compares the access and refresh
tokens before replacing React session state. Equivalent session events keep
the existing state object.

This avoids unnecessary rerenders and repeated protected API requests.

The provider also tracks whether it is still mounted. Late asynchronous
responses are ignored after unmounting.

## Authentication page UI stability

The sign-in and create-account headings now share the same typography and
remain on one line on standard screen sizes. This prevents the form from
shifting vertically when users switch tabs.

The product-panel headline was also reduced so it supports the form rather
than competing with it. On very narrow screens, the auth heading can wrap
instead of overflowing.

Relevant file:

- `web/app/auth/page.module.css`

## Backend clock tolerance

Supabase and Railway do not necessarily have exactly identical clocks. A token
can therefore appear to Railway as being issued a few seconds in the future,
causing:

```text
ImmatureSignatureError: The token is not yet valid (iat)
```

The API JWT verifier accepts a small clock difference through:

```env
JWT_CLOCK_SKEW_SECONDS=30
```

Railway should have the following authentication variables:

```env
AUTH_MODE=supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_JWT_AUDIENCE=authenticated
JWT_CLOCK_SKEW_SECONDS=30
```

Thirty seconds is intended to tolerate ordinary infrastructure clock
differences. It should not be increased substantially to hide persistent clock
or token problems.

## Email confirmation redirects

When account creation began from the workspace form, the auth page preserves
the `next=create-workspace` query parameter in the Supabase confirmation
redirect.

Supabase must allow both production and local auth URLs:

```text
https://supertechstack.vercel.app/auth
http://localhost:3000/auth
```

The Supabase confirmation email template must use `{{ .RedirectTo }}` if the
application supplies a custom redirect.

## Production configuration checklist

Vercel:

```env
NEXT_PUBLIC_API_URL=https://supertechstack-production.up.railway.app
NEXT_PUBLIC_SITE_URL=https://supertechstack.vercel.app
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
```

Railway:

```env
ENVIRONMENT=production
AUTH_MODE=supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_JWT_AUDIENCE=authenticated
JWT_CLOCK_SKEW_SECONDS=30
ALLOWED_ORIGINS=https://supertechstack.vercel.app
```

Redeploy the affected service after changing its environment variables:

- frontend code or Vercel variables: redeploy Vercel;
- backend code or Railway variables: redeploy Railway.

The Railway deployment must run Alembic migration `0003` before serving the
updated workspace creation endpoint. The existing Railway startup process runs
`alembic upgrade head`, so a normal backend deployment should apply it.

## Local development

Start PostgreSQL if it is not already running:

```bash
docker compose -f apps/docker-compose.yml up -d
```

Apply migrations and start the API:

```bash
cd apps/api
alembic upgrade head
uvicorn main:app --reload
```

Start the frontend in another terminal:

```bash
cd apps/web
pnpm dev
```

The frontend development script uses:

```text
next dev --webpack
```

Webpack is used because Turbopack's development manifest intermittently
excluded `/workspaces/[id]`. That caused Next.js to show its own 404 page even
when the API successfully returned the workspace.

If Next.js unexpectedly returns 404 for `/` or `/workspaces/{id}`, stop the
frontend, remove the generated `web/.next` directory, and start `pnpm dev`
again. Do not delete source files.

## Development hydration warnings

Warnings containing attributes such as these are normally caused by browser
extensions modifying the page before React hydrates it:

```text
cz-shortcut-listen
data-new-gr-c-s-check-loaded
data-gr-ext-installed
```

These commonly come from Grammarly or keyboard-shortcut extensions. They are
unrelated to Supabase authentication and API authorization.

The root body uses `suppressHydrationWarning` so extension-generated attributes
do not obscure real development errors. Incognito mode or disabling the
extension is still the cleanest way to confirm the cause.

## Manual test plan

Run these checks in an incognito/private browser window:

1. Open the homepage while signed out.
2. Enter a workspace name and description.
3. Click **Create workspace**.
4. Confirm that the auth page opens on **Create account**.
5. Create and confirm the account.
6. Sign in if confirmation does not create a session automatically.
7. Confirm that the saved workspace is created and opened.
8. Confirm that only one workspace was created.
9. Refresh the workspace several times.
10. Confirm that the user remains signed in.
11. Check Railway logs. A temporary 401 may still occur during a real token
    transition, but it should not create a logout loop. Normal requests should
    settle on 200 responses.

Also verify:

- signing out removes access to private workspaces;
- signing back in restores access;
- the public demo still works without authentication;
- `/workspaces/{id}` loads locally without a Next.js 404;
- one user cannot open another user's private workspace.

## Understanding frontend and API 404 responses

A Next.js log such as:

```text
GET /workspaces/18 404
```

refers to the frontend route on port 3000. It does not necessarily mean the
FastAPI workspace endpoint returned 404.

Compare it with the API log on port 8000:

```text
GET /workspaces/18 HTTP/1.1
```

If the API returns 200 while Next.js returns 404, investigate the frontend
route manifest or `.next` cache. If the API returns 404, verify that the
workspace exists and belongs to the authenticated user.

## If 401 errors continue

Check these items in order:

1. Verify Vercel and Railway use the same Supabase project URL.
2. Verify Railway has `AUTH_MODE=supabase`.
3. Verify `SUPABASE_JWT_AUDIENCE=authenticated`.
4. Verify `JWT_CLOCK_SKEW_SECONDS=30`.
5. Confirm the browser request includes an `Authorization: Bearer ...` header.
6. Decode the token locally and compare its `iss` and `aud` claims with the
   Railway settings. Do not paste production tokens into public websites.
7. Check whether the 401 response says the bearer token is missing or invalid.
   Those indicate different problems.

Do not solve recurring 401 errors by exposing a service-role key or by
disabling backend authentication.

## Verification

The changes have passed:

- `git diff --check`;
- Python syntax compilation for the changed API, migration, and test files.

Idempotency tests are included in
`api/tests/test_workspace_ownership.py`. Run them from the API environment:

```bash
cd apps/api
pytest tests/test_workspace_ownership.py -q
```

If the active Python environment does not have FastAPI and the API
dependencies installed, activate the API virtual environment or run the tests
inside the API container first.
