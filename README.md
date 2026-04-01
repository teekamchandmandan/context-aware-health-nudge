# Context-Aware Health Nudge

This repository contains the Digbi Health product engineering assignment work for a focused Context-Aware Health Nudge vertical slice.

## Source of Truth

The authoritative project plan is in `docs/plan.md`.

Use `docs/plan.md` as the single source of truth for:

- scope boundaries and intentional exclusions
- architecture and stack choices
- confidence handling and escalation behavior
- LLM usage constraints and fallback behavior
- delivery sequencing and documentation expectations

If the plan changes, update `docs/plan.md` first. Keep this README as a concise reviewer-facing entrypoint, not a second decision document.

## Current Status

The repository currently contains planning documentation only. The implementation is intended to follow the plan in `docs/plan.md`.

## Planned Architecture

```text
Member SPA + Coach SPA
        |
        v
   FastAPI backend
        |
        v
      SQLite

Optional LLM phrasing is called only after deterministic nudge selection,
with template fallback on missing key, timeout, or provider failure.
```

For the full rationale, constraints, and behavior details, see `docs/plan.md`.

## Repository Layout

- `docs/assignment.md`: original assignment brief
- `docs/plan.md`: project plan and decision record

## Local Setup

There is no runnable application checked in yet.

For now:

1. Review `docs/assignment.md` for the assignment brief.
2. Review `docs/plan.md` for the proposed implementation.
3. Add implementation code and exact run instructions here once the app exists.

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
- harden seed data, demo polish, and operational documentation

## AI Usage

GitHub Copilot was used to help draft planning documentation, structure repository documentation, and accelerate implementation planning. Final project decisions, scope boundaries, and tradeoffs are manually reviewed and recorded in `docs/plan.md`.