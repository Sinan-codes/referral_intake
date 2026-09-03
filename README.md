# Referral Intake Queue

A single queue that unifies referrals arriving from three unrelated systems (`efax` OCR, `ehr_fhir` FHIR `ServiceRequest`, `web_form`), flags likely duplicates, and lets a coordinator work the queue end to end.

![Referral intake pipeline: three sources normalize into one Referral model, get checked for duplicates by (last_name, dob), are stored in SQLite, served by FastAPI, and consumed by a React SPA whose types are generated from FastAPI's own OpenAPI schema at build time.](backend/docs/pipeline.png)

---

## A note on the stack, up front

The brief asks for a **Node + TypeScript** API. I built the backend in **Python + FastAPI** instead. That's a deliberate deviation from an explicit requirement, not an implementation detail, and I want to own that rather than bury it:

- FastAPI validates requests and responses through Pydantic models, so Part 1’s goal of making decisions explicit in the type system is built into the framework rather than something I had to implement separately.
- FastAPI generates a real OpenAPI schema from those same models for free, which is what makes the "shared types" cross-cutting requirement solvable by generation (`openapi-typescript`) instead of a hand-maintained shared package — see [Shared types](#shared-types-generated-not-hand-mirrored) below.
- I'm most fluent in it, and choosing a framework I already know let me focus on solving the problem rather than learning new tooling.

The tradeoff is real: this diverges from the requested stack and adds Python as a prerequisite alongside Node (see Running it). I’m calling that out explicitly so it’s clear from the outset and can be evaluated as part of the review.

---

## Running it

Two terminals, both from the repo root.

**Backend** — needs [uv](https://docs.astral.sh/uv/) and Python 3.12+:

```bash
cd backend
uv run fastapi dev app/main.py
```

Starts on `http://localhost:8000`. On first boot it creates `db.sqlite3` and seeds it from `backend/seed/referrals-seed.json` — that only happens once; subsequent restarts reuse whatever's already in the table. Delete `db.sqlite3` to force a re-seed.

**Frontend** — needs Node:

```bash
cd frontend
npm install
npm run dev
```

Starts on `http://localhost:5173` and proxies `/referrals` to `localhost:8000` (see `vite.config.ts`) — the backend must already be running.

**Tests** (backend only — see [Tests](#tests)):

```bash
cd backend
uv run pytest
```

---

## What I built

**Part 1 — Normalization.** Each source's normalizer (`backend/app/normalization/`) maps its own record shape onto one internal `Referral` model. Runs once, at startup, from the seed file — a fixed batch of records with no ongoing ingestion in scope, so there's no reason to normalize lazily or re-run it per request. Notable decisions:

- Timestamps arrive in three formats: Unix seconds from `efax`, an offset-aware ISO string from `ehr_fhir`, and a naive local-time string from `web_form`. Each is converted to timezone-aware UTC, while a Pydantic validator on `Referral.received_at` rejects any naive datetime instead of silently assuming a timezone.
- PatientName preserves the original raw_full_name for display and search, while exposing first_name and last_name as optional best-effort fields because parsing names such as “GRACE DELACROIX” or “RENTERIA, MARGUERITE” is inherently heuristic. The optional types make that uncertainty explicit.
- Urgency: three vocabularies collapse onto one `Urgency` enum (`routine` / `urgent` / `stat`). The `web_form` source only has a boolean, which structurally can't express `stat` — a documented lossy mapping, not a bug.
- Missing fields: `referring_provider`, `reason`, and `date_of_birth` are `Optional` on the model; a normalizer only raises `NormalizationError` for the one field a record genuinely can't exist without (e.g. a name). A bad record is skipped, not allowed to take the whole batch down.

**Part 2 — The API.** FastAPI, SQLite (see [Storage](#storage-sqlite) below). `GET /referrals` (status/source/urgency filters, `q` text search on patient name, sort by received date, pagination), `GET /referrals/:id` (includes its duplicate group), `PATCH /referrals/:id/status` (validated against the workflow diagram). Every rejection — a 404, a 409 invalid transition, a 422 validation failure, including ones FastAPI raises itself before a route ever runs — comes back in the same `{ error: { code, message, field } }` envelope, not a different shape depending on which layer rejected it.

**Part 3 — Duplicate detection.** See [Duplicate-matching rule](#duplicate-matching-rule-and-where-it-breaks).

**Part 4 — The frontend.** A React/Vite/Tailwind interface provides a filterable referral queue and a detail view. It shows status, urgency, and duplicate information, supports valid status changes, and includes loading, empty, and error states. Duplicate referrals can be compared side by side.


### Shared types, generated, not hand-mirrored

`backend/scripts/export_openapi.py` calls FastAPI's own `app.openapi()` (introspection only — no server or DB needed) and writes `backend/openapi.json`; `npm run generate:types` in `frontend/` runs `openapi-typescript` against it to produce `frontend/src/api/schema.gen.ts`, which `frontend/src/api/types.ts` re-exports under friendlier names. This closes a real gap I found mid-build: the error envelope was only ever constructed by hand in the exception handlers, so it never showed up in the schema at all — routes now declare `responses={...}` explicitly so 404/409/422 are part of the generated contract too, not just true at runtime.

---

## Duplicate-matching rule, and where it breaks

**The rule:** two referrals match if they share `(last_name, date_of_birth)`, case- and whitespace-insensitive on the name. Matching works across sources and within a single source; a referral missing either field is left out of every group entirely rather than guessed at. A narrow exception to the exact rule exists for OCR noise from `efax` — see the false-negatives discussion below.

**Why not full name:** the seed data has a `web_form` "Bob Barnhardt" and a separate `web_form` "Robert Barnhardt", same DOB — a nickname or spelling variant is a normal thing for two independently-filled-out forms to produce, and requiring exact full-name agreement would hide that pair even though everything else about them lines up.

**Where it breaks — false positives:** dropping first name means two genuinely different patients who happen to share a last name and date of birth get flagged as one. That's accepted, not fixed: in a referral-intake context, a coordinator glancing at an incorrectly-flagged pair and dismissing it costs a few seconds; silently missing a real duplicate costs an afternoon of duplicate work or a patient falling through. The comparison table exists specifically to make that few-seconds check fast — a false positive shows every field disagreeing except the two in the match key, which reads as obviously-not-the-same-person at a glance.

**Where it breaks — false negatives:** anything not captured in `(last_name, dob)` defeats the rule entirely. A transcription error in either field (OCR misreads a birth year, a form is filled in with a maiden vs. married name) means a real duplicate is never flagged, with no fallback signal (phone, address, a fuzzy-name score) backing it up.

One instance of this is addressed: `efax` is OCR output, and OCR occasionally misreads a single character in a name (`Okonkwo` → `Okonkvo`). A referral additionally matches another with the same date of birth if their last names are within one Levenshtein edit (a single substitution, insertion, or deletion) of each other, provided at least one of the two is `efax`-sourced. The source restriction is deliberate: `ehr_fhir` and `web_form` are structured, typed data, not scanned documents, so a mismatch between two of those is a real discrepancy worth a coordinator's attention, not OCR noise to paper over — loosening the last-name match for a pair with no OCR source in it would only add false positives with no corresponding benefit. The seed data includes a demonstration of this: an `efax` record for "Hannah Okonkvo" (DOB 2004-01-10) now correctly groups with the existing `ehr_fhir` record for "Hannah Okonkwo," same DOB — previously two unrelated-looking entries in the queue.

This is narrow by design, and most of the original false-negative surface remains: a DOB transcription error still defeats the rule completely (DOB was deliberately left exact rather than also fuzzed — loosening both fields at once compounds the false-positive risk instead of relocating it, undoing the reason DOB was chosen as the anchor field in the first place). A multi-character OCR error (more than one edit) still isn't caught, nor is a name error originating from `ehr_fhir` or `web_form`. The fix targets the one specific, well-understood failure mode the assignment surfaced — a single-character OCR misread — not fuzzy name matching in general.

**The tension, explicitly:** a stricter key (add first name) trades away the nicknamed-pair case; a looser key (drop DOB, fuzzy-match name) trades toward more false positives on common surnames. I landed on `(last_name, dob)` because DOB is the one field precise enough that two unrelated patients sharing it is rare, and the cost of a false positive (a few seconds of coordinator judgment) is lower than the cost of a false negative (a missed duplicate) in this domain — but that's a judgment call about which failure mode is cheaper, not a fact, and reasonable people could land elsewhere.

---

## Storage: SQLite

One flat `referrals` table, a single long-lived connection opened once in the FastAPI `lifespan` and reused for the process's life (`check_same_thread=False`, since FastAPI dispatches sync routes to a worker thread pool distinct from the thread that opened the connection). For 38 seed records read/written by one process, anything more — a connection pool, Postgres — would be solving a concurrency problem this take-home doesn't have. `possible_duplicate` is deliberately not a column: it's a computed property derived from `duplicate_group_id`, so storing it would just be a second, driftable copy of the same fact.

## Tests

122 tests (`cd backend && uv run pytest`), covering the three places the assignment specifically calls out as high-stakes, plus the HTTP boundary where two real bugs were actually caught during this build (see below):

| File | Covers |
|---|---|
| `test_normalization.py` | Each source's normalizer: happy path, the one field that raises `NormalizationError`, casing/splitting/urgency-mapping quirks, batch skip-bad-keep-good behavior. |
| `test_duplicates.py` | The match key, grouping across and within sources, both decoys the rule is designed to reject, the fuzzy OCR-tolerance tier's scope (distance threshold, `efax`-only restriction, transitive clustering), `apply_duplicate_groups`'s immutability and ordering. |
| `test_status_transition.py` | Enumerates the full status × status grid against the workflow diagram — every allowed pair and every disallowed one, not just the happy path. |
| `test_api.py` | The HTTP boundary itself: the error envelope actually matches on every rejection path (404/409/422, including FastAPI's own validation errors), correct status codes, the duplicate-group response shape. |

`test_api.py` exists because auditing "are errors handled correctly" mid-build turned up two real bugs with zero prior coverage: `sort` was typed as plain `str` with its valid values only in a comment (`?sort=banana` silently fell back to ascending instead of being rejected), and FastAPI's own validation errors bypassed the custom error envelope entirely, coming back in FastAPI's default shape instead of the documented one. Both are fixed; the tests exist so a regression fails loudly instead of quietly.

---

## What I deliberately left out

- **Any of the optional stretch goals.** Optional stretch goals. None were selected deliberately; the focus was on completing and thoroughly testing the four required parts. Basic accessibility improvements, such as visible focus states and properly associated labels, were included as part of the implementation.
- **A shared TypeScript package / monorepo tool.** Generation from the OpenAPI schema does the same job without Nx/Turborepo/pnpm workspaces — see [Shared types](#shared-types-generated-not-hand-mirrored).
- **Optimistic status updates.** A status change waits for the server's response before the UI reflects it. Simpler, and the assignment explicitly lists this as an optional stretch rather than a baseline expectation.
- **An audit trail of status changes.** Only the current status is stored; there's no history of *how* a referral got there. Also an explicitly optional stretch.
- **Case-insensitive search on accented names.** SQLite's default `LIKE` only case-folds ASCII, so a differently-cased accented query (e.g. "rentería" vs "Rentería") won't match. Documented in `db.py` as a known limitation rather than wiring up a full-text extension for one seed record.
- **Auth, deployment/CI, Docker, real-time updates, i18n, real HIPAA compliance** — all explicitly out of scope in the brief.

## What I'd do next with another day

- **Optimistic status updates with rollback** — the stretch goal I'd pick if picking one. The status workflow is small and well-defined enough that showing the new state immediately and rolling back on a 409 is low-risk and would make the queue feel meaningfully more responsive.
- **A genuine keyboard-and-screen-reader pass** — arrow-key navigation through the queue table, an `aria-live` region for async state changes (a status update succeeding/failing, a page of results loading), rather than the focus-ring-and-labels baseline that's there now.
- **Filter/sort state in the URL** — cheap with `react-router`'s `useSearchParams`, and turns "here's a filtered view" from a verbal instruction into a link a coordinator can actually share.
- **A root-level convenience script** (`dev.sh` or a `Makefile` target) to start both servers with one command, since the two-terminal, two-language-runtime setup is real friction for anyone just trying to run this.
- **Automatic type regeneration** — a file watcher or a pre-`dev` hook that re-runs the OpenAPI export + `openapi-typescript` pipeline when the backend's models change, instead of a manual two-command step.
- **Postgres**, if this ever needed concurrent writers — SQLite's single-writer model is a fine fit for this scale, not for a real multi-coordinator clinic.
