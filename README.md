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

The repository currently contains planning documentation only. Implementation should follow `docs/plan.md` and the phase specs in `docs/`.

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

There is no runnable application checked in yet.

For now:

1. Review `docs/assignment.md` for the assignment brief.
2. Review `docs/plan.md` for the proposed implementation.
3. Use the phase files as the branch-by-branch execution plan.
4. Add implementation code and exact run instructions here once the app exists.

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
