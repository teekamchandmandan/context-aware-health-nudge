# Phase 03: API Contracts

## Objective

Define and implement the backend API surface that exposes member decisions, records member actions, and supports the coach workflow.

## Suggested Branch

`phase/03-api-contracts`

## Why This Phase Exists

Stable contracts let frontend work proceed without guessing at backend behavior. This phase should make the system callable, predictable, and easy to demo.

## Dependencies

- [phase-01-foundation-and-data.md](./phase-01-foundation-and-data.md)
- [phase-02-decision-engine.md](./phase-02-decision-engine.md)

## In Scope

- Implement `GET /api/members/{member_id}/nudge`.
- Implement `POST /api/nudges/{nudge_id}/action`.
- Implement `GET /api/coach/nudges`.
- Implement `GET /api/coach/escalations`.
- Implement `POST /api/members/{member_id}/signals` for demo or seed extension.
- Define request and response models with explicit types and defaults.
- Return clear error behavior for missing members, invalid actions, and unavailable nudges.

## Out of Scope

- Frontend rendering.
- LLM phrasing quality.
- Rich pagination, auth, or production-grade API versioning.

## Deliverables

- FastAPI route handlers for all planned endpoints.
- Pydantic models or equivalent request and response schemas.
- Side effects for action recording, status transitions, and escalation creation on `ask_for_help`.
- API responses that include the fields later phases need for member and coach views.

## API Conventions

- All responses are JSON.
- All timestamps are UTC ISO 8601 strings.
- Missing resources return `404`.
- Validation failures return `422`.
- Invalid state transitions return `409`.
- Coach list endpoints accept `limit`, default to `20`, and cap at `50`.

## Response Shapes

### Member nudge response

Successful responses should always include a `state` field.

```json
{
  "state": "active",
  "member": { "id": "member_meal_01", "name": "Maya" },
  "nudge": {
    "id": "nudge_123",
    "nudge_type": "meal_guidance",
    "content": "Try a lighter, lower-carb dinner to balance today's lunch.",
    "explanation": "You logged a higher-carb meal today and your goal is low carb.",
    "matched_reason": "recent_meal_high_carb_for_low_carb_goal",
    "confidence": 0.86,
    "escalation_recommended": false,
    "status": "active",
    "phrasing_source": "template",
    "created_at": "2026-04-02T18:30:00Z"
  }
}
```

Empty and escalated cases should stay explicit instead of relying on `204`:

```json
{
  "state": "no_nudge",
  "member": { "id": "member_weight_01", "name": "Ava" },
  "nudge": null
}
```

```json
{
  "state": "escalated",
  "member": { "id": "member_support_01", "name": "Jordan" },
  "nudge": null,
  "escalation_created": true
}
```

### Action response

```json
{
  "nudge_id": "nudge_123",
  "action_type": "dismiss",
  "nudge_status": "dismissed",
  "escalation_created": false,
  "recorded_at": "2026-04-02T18:35:00Z"
}
```

### Coach list response

```json
{
  "items": [],
  "limit": 20,
  "count": 0
}
```

## Signal Intake Contract

- Allowed `signal_type` values are `meal_logged`, `weight_logged`, and `mood_logged`.
- Minimum payload fields:
  - `meal_logged`: `meal_type`, `carbs_g`
  - `weight_logged`: `weight_lb`
  - `mood_logged`: `mood`
- Reject unknown signal types or missing required payload fields with `422`.

## API Responsibilities

### `GET /api/members/{member_id}/nudge`

- Return the current active nudge if one already exists.
- Otherwise invoke decisioning, persist the resulting nudge if applicable, and return it.
- Return an explicit empty state if no nudge should be shown.
- If decisioning recommends escalation, create it and return `state: "escalated"` with no member-visible nudge.

### `POST /api/nudges/{nudge_id}/action`

- Accept exactly `act_now`, `dismiss`, or `ask_for_help`.
- Persist the user action.
- Update nudge status.
- Create an escalation automatically for `ask_for_help`.
- Reject repeated actions against terminal nudges with `409`.

### `GET /api/coach/nudges`

- Return recent nudges with member name, content, explanation, matched reason, confidence, escalation recommendation, and latest user response.
- Default to the most recent 20 records ordered by `created_at DESC`.

### `GET /api/coach/escalations`

- Return open escalations with member name, reason, source, status, and timestamp.
- Default to the most recent 20 open escalations ordered by `created_at DESC`.

### `POST /api/members/{member_id}/signals`

- Accept a mocked signal payload for demo or scenario extension.
- Persist the signal and return the stored record.

## Implementation Notes

- Make active nudge retrieval idempotent from the API boundary, not just inside the engine.
- Keep action handling strict so invalid transitions fail clearly.
- Preserve enough response detail that frontend branches do not need extra endpoints.
- Add simple filtering or ordering only if it does not complicate the API surface materially.
- Repeated `GET /nudge` calls should return the same active nudge until it reaches a terminal state.

## Recommended Work Breakdown

1. Define request and response models.
2. Implement member-facing endpoints.
3. Implement coach-facing endpoints.
4. Add action-driven side effects and escalation creation.
5. Verify the endpoint behavior against seeded scenarios.

## Acceptance Criteria

- Every endpoint listed in the project plan exists and returns predictable structured responses.
- The nudge endpoint is idempotent for repeated reads.
- `ask_for_help` creates an escalation automatically.
- Coach endpoints expose enough context to avoid extra follow-up API work.
- Error responses are clear enough for UI handling.
- Empty and escalated member states are explicit and frontend-safe.

## Verification

- Call each endpoint manually or through API docs and confirm the expected payload shape.
- Verify repeated `GET /nudge` calls do not create duplicate active nudges.
- Verify invalid action types are rejected.
- Verify `ask_for_help` creates an escalation visible in the coach endpoint.

## Merge Checkpoint

Merge when frontend work can begin against stable API behavior without inventing mocks that disagree with the backend.
