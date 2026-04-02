# Phase 01: Foundation and Data

## Objective

Establish the project baseline: repository structure, backend bootstrap, SQLite persistence, domain schema, and seed data for the three planned scenarios.

## Suggested Branch

`phase/01-foundation-and-data`

## Why This Phase Exists

Every later branch depends on stable entities, repeatable local setup, and realistic sample data. This phase should land a clean baseline without taking on decisioning, UI, or LLM work.

## Dependencies

None. This is the starting point.

## Default Technical Baseline

| Area               | Default                                                                             |
| ------------------ | ----------------------------------------------------------------------------------- |
| Backend language   | Python 3.12                                                                         |
| API framework      | FastAPI                                                                             |
| Validation         | Pydantic                                                                            |
| Client placeholder | Vite + React scaffold may exist, but Phase 01 does not need member or coach screens |
| Database           | SQLite using raw SQL bootstrap scripts or a very small initialization layer         |
| Time handling      | UTC only                                                                            |
| Seed identifiers   | Stable text IDs rather than auto-increment assumptions                              |

## In Scope

- Establish the initial repository structure for client, server, and shared docs.
- Set up a FastAPI application shell with local run instructions.
- Add SQLite initialization and schema creation for the six planned tables.
- Define the core domain entities: members, signals, nudges, nudge actions, escalations, and audit events.
- Add seed data for the meal mismatch, missed weight logging, and support-risk scenarios.
- Add one previously acted nudge and one previously dismissed nudge so later phases can validate history-aware logic.
- Scaffold the client directory with Vite + React + TypeScript + Tailwind CSS v4 so Phase 04 can begin UI work without setup overhead.
- Add a dev-only `POST /debug/reset-seed` endpoint (guarded by `DEBUG=true` env var) to support deterministic demo resets.

## Out of Scope

- Nudge evaluation rules or confidence scoring.
- Member or coach UI.
- LLM integration.
- Detailed analytics or observability beyond the schema placeholders already required.

## Deliverables

- Backend app entrypoint that starts locally.
- SQLite schema creation mechanism.
- Seed workflow that can repopulate the local database deterministically.
- Initial data access conventions for timestamps, JSON payload fields, and status enums.
- Brief setup notes so later phases build on the schema instead of bypassing it.

## Repository Shape

The first branch should establish a minimal but durable layout.

- `server/` for FastAPI application code, schema bootstrap, and seed scripts
- `client/` as a Vite + React + TypeScript + Tailwind CSS scaffold (established in this phase)
- `docs/` for planning and delivery notes
- `data/` only if a checked-in SQLite file is needed for a demo snapshot; otherwise generate locally and ignore it

## Schema Conventions

- Use UTC timestamps for all persisted times.
- Prefer text IDs for seeded members, such as `member_meal_01`, `member_weight_01`, and `member_support_01`.
- Keep `profile_json` for member preferences and `payload_json` for signal details only.
- Treat `generated_by` as `rule_engine` from day one so later phases do not overload it for phrasing source.
- Keep schema creation idempotent with `CREATE TABLE IF NOT EXISTS` and a single reset-and-seed command.

## Required Enum Values

- `signal_type`: `meal_logged`, `weight_logged`, `mood_logged`
- `nudge_type`: `meal_guidance`, `weight_check_in`, `support_risk`
- `nudge.status`: `active`, `acted`, `dismissed`, `escalated`
- `nudge_actions.action_type`: `act_now`, `dismiss`, `ask_for_help`
- `escalations.status`: `open`, `resolved`
- `nudges.phrasing_source`: `template`, `llm`

## Seed Fixtures

The seed set should use stable demo members and enough chronology to support later tests.

| Member ID           | Goal          | Purpose                 | Minimum seeded signals                                                                       |
| ------------------- | ------------- | ----------------------- | -------------------------------------------------------------------------------------------- |
| `member_meal_01`    | `low_carb`    | Meal mismatch scenario  | One `meal_logged` signal in the last 24 hours with `carbs_g >= 60`                           |
| `member_weight_01`  | `weight_loss` | Missing weight scenario | No `weight_logged` signal in the last 4 full days                                            |
| `member_support_01` | `balanced`    | Support-risk scenario   | One `mood_logged` signal with `mood: low` in the last 3 days and two recent dismissed nudges |

Example payload shapes:

- `meal_logged`: `{ "meal_type": "lunch", "carbs_g": 72, "protein_g": 18 }`
- `weight_logged`: `{ "weight_lb": 182.4 }`
- `mood_logged`: `{ "mood": "low", "note": "Feeling off plan this week" }`

## Implementation Notes

- Prefer a small, explicit schema over an abstraction-heavy model layer.
- Keep JSON columns limited to fields that are genuinely variable, such as profile or signal payloads.
- The `POST /debug/reset-seed` endpoint is registered only when the `DEBUG` environment variable is set to `true`. It is not mounted in non-debug mode.
- Use stable seed member identities so frontend and API work can reliably reference them.
- Make schema creation idempotent so branch rebases and reruns stay low-friction.
- Add only the minimum application structure needed to support later phases cleanly.
- Do not add migration tooling yet unless schema evolution becomes hard to reason about. A bootstrap script is enough for this phase.

## Recommended Work Breakdown

1. Create the backend application skeleton and local configuration conventions.
2. Define the SQLite schema and initialize the database on first run.
3. Add seed data covering all three core assignment scenarios.
4. Verify the data can be queried and reset reliably.
5. Document the shape of seeded members and signals for future phases.

## Acceptance Criteria

- A local developer can start the backend without manual database setup.
- The database includes all six planned tables with the fields defined in the project plan.
- Seed data covers the meal mismatch, missed weight logging, and support-risk cases.
- Seed data includes historical nudge actions so fatigue, dismissal, and escalation behavior can be tested later.
- The repository has a clear implementation starting point without forcing client UI or AI work into this branch.
- Stable seeded member IDs and enum values are documented so later branches do not invent alternatives.

## Verification

- Start the backend and confirm database initialization succeeds.
- Reset and reseed the database at least once to confirm deterministic setup.
- Inspect the seeded rows to confirm all core scenarios are present.
- Confirm no decision logic or UI behavior is embedded in this phase.
- Confirm the seed set includes at least one acted nudge and two dismissed nudges tied to the support-risk member.

## Merge Checkpoint

Merge when the schema and seed data are stable enough that later branches can build on them directly.
