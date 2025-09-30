# Marketing Backend

## Overview

Node/Express service with a 5‑minute incremental Upwork job fetcher and per‑profile proposal generation using OpenAI Assistants. Proposals are generated only when a profile’s score ≥ 80.

## Key Components

- `index.js`: Express app, routes, middleware, and pipeline bootstrap
- `upworkFetcher.js`: Incremental fetch, internal filtering per company/profile, assistant scoring, proposal writes
- `assistant.js`: Self‑healing Assistants API initialization (recreates if stale)
- `controllers/*`: Auth, profiles, filters, proposals, chat
- `middleware/auth.js`: JWT auth with company scope
- `db.js`: PostgreSQL client
- `tools/upworkServices.js`: Optional dev CLI for Upwork Rooms/Messages

## Data Model (core)

- `upwork_jobs(job_id UNIQUE, title, job_data JSONB)`
- `profiles(id, company_id, name, content, training_file, last_updated, assistant_id)`
- `job_filters(platform='upwork', company_id, profile_id NULLABLE, active, category_ids, workload, verified_payment_only, client_hires_min/max, hourly_rate_min/max, budget_min/max, proposal_min/max, experience_level)`
- `proposal_feedback(id, profile_id, job_id, proposal, thread_id, score, created_at)`
- `profile_chat_threads(id, profile_id, thread_id, title, updated_at)`
- `profile_chat_messages(id, profile_id, thread_id, role, content/enc, created_at)`

## Pipeline (every 5 minutes)

1) Fetch new jobs since `lastFetchedAt` (first run = last 24h) and store each to `upwork_jobs` (full `job_data`).
2) For each company and each profile, choose filter: profile filter > company filter > none.
3) For each job, apply the chosen filter. If it passes, reuse/create the profile’s chat thread and ask the assistant to return strict JSON `{score, suitable, proposal}`.
4) If `score ≥ 80` and suitable, insert into `proposal_feedback`. Never duplicate `(job_id, profile_id)`.

## Setup

1) Create `.env` in backend root with:

```
CLIENT_ID=...
CLIENT_SECRET=...
REFRESH_TOKEN=...     # or use AUTH_CODE to exchange once
REDIRECT_URI=http://localhost:3009/callback
OPENAI_API_KEY=sk-...
DB_HOST=...
DB_PORT=5432
DB_USER=...
DB_PASSWORD=...
DB_NAME=...
DB_SSL=false
```

2) Install and run:

```
npm install
npm run upwork:url        # prints auth URL (if no refresh token)
npm run upwork:exchange   # exchanges AUTH_CODE into tokens
npm start                 # starts API + job pipeline
```

## Logging

Structured JSON logs:

- `filter.used`: which filter scope used per profile, and how many jobs passed
- `score`: per job score and whether saved
- `pipeline.done`: summary per run

## Notes

- Embeddings are not used; matching is filters + assistant scoring.
- `Uploads/` is for profile training files and should be git‑ignored.


