# MoDora Web Productization Implementation Plan

## Target

MoDora should evolve from a single-user research tool into a multi-user web service with the following topology:

- `modora.pro`: marketing/home page
- `modora.pro/demo`: MoDora frontend
- `api.modora.pro`: backend API

The service must support:

- user registration and login
- per-user data isolation
- persistent storage
- future migration to a database-backed architecture without reworking the public API


## Current Gaps

The current codebase is still centered on a single shared workspace model:

- document storage is global
- cache storage is global
- knowledge base state is global
- task status is keyed by filename in memory
- many API routes still use `file_name` as the primary identifier

This is incompatible with a production multi-user deployment model.


## Architecture Decisions

The following decisions should be treated as baseline unless changed explicitly.

### 1. Public Routing

- `modora.pro` serves the home page
- `modora.pro/demo` serves the built frontend application
- `api.modora.pro` serves FastAPI

### 2. Authentication

Preferred first implementation:

- secure cookie-based auth
- `HttpOnly`
- `Secure`
- cross-subdomain compatible

Rationale:

- frontend and API are on sibling subdomains
- cookie-based auth reduces frontend token handling complexity
- easier to harden for browser-based use

### 3. Persistence

Preferred first implementation:

- SQLite for user accounts, document metadata, jobs, and sessions
- local filesystem for uploaded files and generated artifacts

Rationale:

- low operational cost
- fast to implement
- compatible with later migration to PostgreSQL and object storage

### 4. Resource Identity

All public-facing document workflows should move toward:

- `document_id`
- `job_id`

and away from:

- raw `file_name` as the primary identifier


## Implementation Phases

## Phase 0: Freeze Product Scope

Before coding, confirm the following:

1. Whether registration is open to the public or invite-only
2. Whether uploaded documents are private by default
3. Whether admin functionality is needed in v1
4. Whether model configuration changes remain admin-only
5. Maximum upload size and expected concurrency

Deliverable:

- a short written scope note for v1


## Phase 1: Deployment Topology

Goal:

- establish the final production access pattern

Tasks:

1. Split homepage and demo frontend
- deploy homepage static assets at `modora.pro`
- deploy MoDora frontend build at `modora.pro/demo`

2. Separate API host
- deploy backend at `api.modora.pro`
- keep Cloudflare `Full (strict)`

3. Update reverse proxy
- `modora.pro /` -> homepage static files
- `modora.pro /demo/` -> frontend static files
- `api.modora.pro /api/` -> FastAPI
- `api.modora.pro /health` -> FastAPI health endpoint

4. Use production runtime only
- backend via systemd
- no dev server exposure
- no Vite production dependency
- no `--reload` in production

Deliverables:

- updated Nginx config
- backend systemd service for production
- frontend build and publish path under `/demo`


## Phase 2: Authentication System

Goal:

- introduce a minimal but production-oriented account system

Tasks:

1. Add user model
- `id`
- `email`
- `password_hash`
- `created_at`
- `status`

2. Add auth routes
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

3. Add session handling
- secure cookie session or equivalent signed session design
- expiration and logout

4. Add minimum protections
- password hashing
- login rate limit
- session expiration
- basic audit logging

5. Frontend changes
- login page
- registration page
- authenticated app shell
- boot-time current-user check

Deliverables:

- working register/login/logout flow
- frontend protected routes


## Phase 3: User-Scoped Storage

Goal:

- eliminate the global shared workspace model

Tasks:

1. Introduce per-user storage root

Recommended layout:

- `storage/users/{user_id}/docs/`
- `storage/users/{user_id}/cache/`
- `storage/users/{user_id}/kb/`

2. Refactor path resolution
- path resolution must accept user context
- all document/cache/kb access must derive from authenticated user

3. Refactor task state
- replace in-memory filename-based status tracking
- use user-aware persistent job tracking

4. Refactor file access
- replace global static file exposure with authenticated access control
- validate that requested resources belong to current user

Deliverables:

- no document or cache lookup should rely on global shared directories
- file access tied to authenticated user ownership


## Phase 4: Resource ID Refactor

Goal:

- move APIs from filename-oriented access to stable resource IDs

Tasks:

1. Add document records
- `documents.id`
- `documents.user_id`
- `documents.original_name`
- `documents.storage_key`
- `documents.status`
- `documents.created_at`

2. Add job records
- `jobs.id`
- `jobs.user_id`
- `jobs.document_id`
- `jobs.type`
- `jobs.status`
- `jobs.error`
- `jobs.created_at`

3. Update API contract
- upload returns `document_id` and `job_id`
- chat/tree/stats/pdf/delete use `document_id`
- filenames remain display data only

4. Update frontend state
- sessions store `document_id` and display name
- API calls stop depending on raw filenames

Deliverables:

- all new API paths and payloads centered on IDs


## Phase 5: Metadata Persistence

Goal:

- persist application state needed for multi-user operation

Tasks:

1. Introduce SQLite schema
- users
- sessions
- documents
- jobs
- conversations
- conversation_documents

2. Add repository/service layer
- avoid embedding storage logic directly in routers
- keep persistence swappable

3. Keep filesystem for large artifacts
- uploaded PDFs
- OCR output
- tree output
- derived files

Deliverables:

- persistent metadata across service restarts
- schema ready for later PostgreSQL migration


## Phase 6: API Security Cleanup

Goal:

- remove or restrict routes that are unsafe in a public deployment

Tasks:

1. Restrict config mutation
- configuration write APIs should be admin-only or disabled in public mode

2. Restrict destructive routes
- delete routes must require authentication and ownership checks

3. Tighten CORS
- allow only approved production origins

4. Tighten uploads
- file type validation
- upload size limit
- per-user rate limit
- per-user concurrency guard

5. Remove unauthenticated global file exposure
- no shared static mount for all uploaded documents

Deliverables:

- public API surface reduced to safe authenticated routes


## Phase 7: Frontend Productization

Goal:

- convert the research frontend into a real product frontend

Tasks:

1. Add route structure
- `/demo/login`
- `/demo/register`
- `/demo/app`

2. Add authenticated app state
- current user
- personal documents
- upload queue
- processing states

3. Standardize API base usage
- frontend should target `https://api.modora.pro`
- remove production dependence on Vite dev proxy assumptions

4. Handle auth failures cleanly
- redirect on 401
- clear session state on logout

Deliverables:

- deployable frontend that works from `/demo`


## Phase 8: Production Validation

Goal:

- verify the system behaves correctly as a multi-user service

Validation checklist:

1. Anonymous users cannot access private resources
2. User A cannot see user B documents, trees, stats, or files
3. Duplicate filenames do not collide
4. Restart does not lose account or document metadata
5. Upload -> process -> view -> chat flow works end to end
6. Login state survives refresh correctly
7. Delete only affects user-owned resources
8. `/demo` routing works on refresh and direct navigation


## Recommended Execution Order

1. Production routing and deployment split
2. Authentication foundation
3. User-scoped storage
4. `document_id` and `job_id` refactor
5. SQLite metadata persistence
6. API hardening
7. Frontend productization and validation


## Initial Data Model Draft

### users

- `id`
- `email`
- `password_hash`
- `status`
- `created_at`

### sessions

- `id`
- `user_id`
- `expires_at`
- `created_at`

### documents

- `id`
- `user_id`
- `original_name`
- `storage_key`
- `status`
- `created_at`

### jobs

- `id`
- `user_id`
- `document_id`
- `type`
- `status`
- `error`
- `created_at`

### conversations

- `id`
- `user_id`
- `title`
- `created_at`

### conversation_documents

- `conversation_id`
- `document_id`


## Priority Code Areas

The following files are the first places that will need redesign:

- `MoDora-backend/src/modora/core/utils/paths.py`
- `MoDora-backend/src/modora/core/services/task_store.py`
- `MoDora-backend/src/modora/api/v1/documents.py`
- `MoDora-backend/src/modora/api/v1/chat.py`
- `MoDora-backend/src/modora/api/v1/tree.py`
- `MoDora-backend/src/modora/api/v1/stats.py`
- `MoDora-backend/src/modora/api/v1/kb.py`
- `MoDora-backend/src/modora/api/v1/model_instances.py`
- `MoDora-frontend/src/composables/useModoraStore.js`
- `deploy/nginx/modora.pro.conf`


## Milestone Proposal

### Week 1

- finalize deployment topology
- deploy homepage and demo separately
- make API reachable at `api.modora.pro`

### Week 2

- implement registration/login/logout/me
- wire frontend auth flow
- add SQLite base schema

### Week 3

- implement user-scoped storage
- add document metadata and persistent jobs
- replace filename-based routing where necessary

### Week 4

- migrate chat/tree/stats/pdf flows to user-aware model
- harden public API surface
- run production validation and launch checklist


## Non-Goals For First Public Version

The following should not block v1 unless explicitly required:

- full admin panel
- third-party OAuth
- object storage migration
- PostgreSQL migration
- fine-grained team/workspace sharing
- public document sharing links


## Success Criteria

The implementation is considered complete for v1 when:

- users can register and log in
- each user sees only their own data
- data persists across restarts
- frontend is served from `modora.pro/demo`
- API is served from `api.modora.pro`
- public routes are appropriately restricted
- the service no longer depends on the current single-user shared-path model
