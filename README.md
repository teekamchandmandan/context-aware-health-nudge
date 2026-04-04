# Context-Aware Health Nudge

This repository contains a focused Context-Aware Health Nudge vertical slice.

## Source of Truth

The authoritative decision record is in `docs/plan.md`.

Update `docs/plan.md` first whenever any of the following change:

- scope boundaries and intentional exclusions
- architecture and stack choices
- confidence handling and escalation behavior
- LLM usage constraints and fallback behavior
- delivery sequencing and documentation expectations

Keep this README as the reviewer-facing entrypoint, not a second planning document.

## Current Status

The repository now includes the core vertical slice: deterministic decisioning, member and coach flows, SQLite persistence, seeded demo scenarios, and optional LLM-assisted phrasing with deterministic fallback. The remaining docs now include a dedicated UI/UX redesign phase before the final delivery pass.

## Planned Architecture

```text
Member SPA + Coach SPA (React)
        |
        v
   FastAPI backend
        |
        v
      SQLite

Optional LLM phrasing is called only after deterministic nudge selection,
with template fallback on missing key, timeout, or provider failure.
```

The planned stack is a Vite + React SPA on the client and FastAPI + SQLite on the backend. For the full rationale, constraints, and behavior details, see `docs/plan.md`.

## Repository Layout

- `server/`: FastAPI app shell, SQLite bootstrap, and seed workflow
- `client/`: Vite + React + Tailwind scaffold
- `docs/assignment.md`: original assignment brief
- `docs/plan.md`: project plan and decision record
- `docs/phase-01-foundation-and-data.md` through `docs/phase-09-quality-demo-and-delivery.md`: branch-friendly implementation specs

## Implementation Order

Review and implement the phase specs in sequence:

1. `docs/phase-01-foundation-and-data.md`
2. `docs/phase-02-decision-engine.md`
3. `docs/phase-03-api-contracts.md`
4. `docs/phase-04-member-experience.md`
5. `docs/phase-05-coach-experience.md`
6. `docs/phase-06-llm-safety-and-phrasing.md`
7. `docs/phase-07-observability-and-audit.md`
8. `docs/phase-08-ui-ux-redesign.md`
9. `docs/phase-09-quality-demo-and-delivery.md`

## Local Setup

The project runs locally with or without an OpenAI API key. If `OPENAI_API_KEY` is not set, the backend uses deterministic template phrasing by default.

### Backend

1. Create and activate a Python virtual environment in `server/`.
2. Install dependencies:

```bash
cd server
pip install -r requirements.txt
```

3. Create your local env file:

```bash
cp .env.example .env
```

4. Edit `server/.env` and add `OPENAI_API_KEY` if you want LLM phrasing enabled.

5. Seed the local database:

```bash
python -m app.seed
```

6. Start the API:

```bash
uvicorn app.main:app --reload
```

7. Verify the key endpoints:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/debug/reset-seed
curl http://127.0.0.1:8000/api/members/member_meal_01/nudge
curl http://127.0.0.1:8000/api/coach/nudges
```

Without an API key, `GET /api/members/{member_id}/nudge` returns template phrasing. With a valid key, newly created active nudges may be upgraded to `phrasing_source = "llm"` after validation. Existing active nudges are returned as-is and are not re-phrased on repeated reads.

### Environment Variables

Server variables loaded from `server/.env`:

| Variable                   | Default           | Purpose                                                                    |
| -------------------------- | ----------------- | -------------------------------------------------------------------------- |
| `DEBUG`                    | `false`           | Enables local-only debug behavior such as `POST /debug/reset-seed`.        |
| `OPENAI_API_KEY`           | unset             | Enables optional LLM phrasing for newly created active nudges.             |
| `OPENAI_MODEL`             | `gpt-4.1-mini`    | Selects the OpenAI model used by the phrasing layer.                       |
| `PHRASING_TIMEOUT_SECONDS` | `3`               | Sets the timeout for provider calls before deterministic fallback.         |
| `DATABASE_PATH`            | `server/nudge.db` | Overrides the SQLite database path. Prefer an absolute path if customized. |

Client variables:

| Variable       | Default                 | Purpose                                   |
| -------------- | ----------------------- | ----------------------------------------- |
| `VITE_API_URL` | `http://localhost:8000` | Backend base URL used by the Vite client. |

The client already includes committed local-development defaults in `client/.env.development`.

For most users:

1. Leave `client/.env.development` alone.
2. If you need a different backend URL, copy `client/.env.example` to `client/.env.local`.
3. Edit `client/.env.local` with your own `VITE_API_URL`.

Example:

```bash
cd client
cp .env.example .env.local
```

This works with Vite as expected: `client/.env.development` provides the committed default for local development, and `client/.env.local` is the right per-developer override file. The local file is ignored by git, so newcomers can safely add their own URL without modifying a committed file.

### Client

```bash
cd client
npm install
npm run dev
```

The client includes both member and coach surfaces. The member card shows phrasing provenance, and the coach dashboard exposes phrasing source alongside confidence and matched reason.

### Planning Docs

1. Review `docs/assignment.md` for the assignment brief.
2. Review `docs/plan.md` for the current implementation direction.
3. Use the phase files as the branch-by-branch execution plan.

## Demo Reset (Admin Only)

The member and coach UIs do not expose a reset control — neither role should need to know the database can be wiped. To reset the database to its seeded state during a demo or review session, run the following command while the backend is running:

```bash
curl -X POST http://127.0.0.1:8000/debug/reset-seed
```

This endpoint is only available when `DEBUG=true` is set in `server/.env`. It re-runs the seed script, restoring all seeded members, signals, and nudges to their original state.

## What Is Intended To Be Built

The planned submission is a small end-to-end vertical slice that includes:

- a member-facing nudge experience with act now, dismiss, and ask for help actions
- a backend decision engine with explicit confidence handling
- escalation to a coach for low-confidence or help-seeking cases
- a coach-facing view for recent nudges and open escalations
- audit logging and bounded LLM-assisted phrasing

Detailed behavior, tradeoffs, and exclusions remain in `docs/plan.md`.

## If I Had Two More Weeks

- deepen automated test coverage for decisioning, idempotency, and fallback behavior
- improve coach workflow usability and filtering without expanding scope into dashboards
- harden seed data, demo polish, and operational documentation so a reviewer can run the project in under ten minutes

## AI Usage

GitHub Copilot was used to help draft planning documentation, structure repository documentation, and accelerate implementation planning. Final scope decisions, constraints, and tradeoffs are manually reviewed and recorded in `docs/plan.md`.
