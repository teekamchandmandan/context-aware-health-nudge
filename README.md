# Context-Aware Health Nudge

This repository contains the Digbi Health product engineering assignment for a focused Context-Aware Health Nudge vertical slice.

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

The repository includes the Phase 01 baseline: a FastAPI backend shell, SQLite schema bootstrap, deterministic seed workflow, and a Vite + React + Tailwind client scaffold. Later phases in `docs/` describe the member flow, coach flow, decision engine, and delivery work that still needs to be built.

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
- `docs/phase-01-foundation-and-data.md` through `docs/phase-08-quality-demo-and-delivery.md`: branch-friendly implementation specs

## Implementation Order

Review and implement the phase specs in sequence:

1. `docs/phase-01-foundation-and-data.md`
2. `docs/phase-02-decision-engine.md`
3. `docs/phase-03-api-contracts.md`
4. `docs/phase-04-member-experience.md`
5. `docs/phase-05-coach-experience.md`
6. `docs/phase-06-llm-safety-and-phrasing.md`
7. `docs/phase-07-observability-and-audit.md`
8. `docs/phase-08-quality-demo-and-delivery.md`

## Local Setup

Phase 01 provides a runnable backend foundation and a client scaffold.

### Backend

1. Create and activate a Python virtual environment in `server/`.
2. Install dependencies:

```bash
cd server
pip install -r requirements.txt
```

3. Seed the local database:

```bash
python -m app.seed
```

4. Start the API:

```bash
DEBUG=true uvicorn app.main:app --reload
```

5. Verify the baseline endpoints:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/debug/reset-seed
```

The backend currently exposes only the Phase 01 shell endpoints: `GET /health` and the dev-only `POST /debug/reset-seed`.

### Client

```bash
cd client
npm install
npm run dev
```

The client is still the Phase 01 scaffold. Member and coach product surfaces land in later phases.

### Planning Docs

1. Review `docs/assignment.md` for the assignment brief.
2. Review `docs/plan.md` for the current implementation direction.
3. Use the phase files as the branch-by-branch execution plan.

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
