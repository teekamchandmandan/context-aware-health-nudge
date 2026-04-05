# Phase 02: Decision Engine

## Objective

Implement deterministic nudge selection with explicit evaluator functions, confidence tiers, fatigue controls, and safe escalation behavior.

## Suggested Branch

`phase/02-decision-engine`

## Why This Phase Exists

The assignment is easier to trust if nudge creation is explainable before any API or UI polish is added. This phase should make the core product logic concrete and testable.

## Dependencies

- [phase-01-foundation-and-data.md](./phase-01-foundation-and-data.md)

## In Scope

- Implement `check_meal_goal_mismatch`.
- Implement `check_missing_weight_log`.
- Implement `check_support_risk`.
- Evaluate all candidates for a member and choose a single best outcome.
- Apply confidence tiers: high, medium, and low.
- Enforce fatigue rules: no duplicate active nudge, cooldown by nudge type, and daily cap.
- Route low-confidence outcomes to escalation rather than auto-delivery.

## Out of Scope

- HTTP contract design beyond what is needed to call the engine internally.
- Frontend rendering.
- LLM phrasing.
- Rich analytics or dashboards.

## Deliverables

- A decision engine module with explicit evaluator functions.
- A candidate format that includes nudge type, matched reason, explanation basis, confidence, and escalation recommendation.
- A selection flow that is deterministic and idempotent for active-nudge retrieval.
- Clear transitions for `active`, `acted`, `dismissed`, and `escalated` states, with `delivered_at` tracked separately from status.

## Default Evaluator Rules

| Evaluator                  | Trigger                                                                                                  | Candidate type    | Default confidence                |
| -------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------- | --------------------------------- |
| `check_meal_goal_mismatch` | Member goal is `low_carb` and the most recent meal in the last 24 hours has `meal_profile = higher_carb` | `meal_guidance`   | `0.70` base (computed 0.78–0.90)  |
| `check_missing_weight_log` | No `weight_logged` signal in the last 4 full UTC days                                                    | `weight_check_in` | `0.50` base (computed 0.50–0.76)  |
| `check_support_risk`       | `mood_logged.mood == "low"` in the last 3 days and at least 2 `dismiss` actions in the last 7 days       | `support_risk`    | `0.25` base (hard-capped at 0.48) |

These base values are starting points. Computed confidence applies evidence-weighted adjustments (recency, classification clarity, overdue severity, member engagement, and dismissal patterns) documented in `server/app/engine/confidence.py`. Each adjustment is recorded as a named factor for auditability. If base values change, update this file and `docs/plan.md` together.

## Candidate Contract

Each evaluator should return either `None` or a candidate with these fields:

- `nudge_type`
- `matched_reason`
- `explanation_basis`
- `confidence`
- `confidence_factors` — list of `{name, value, label}` dicts explaining each scoring adjustment
- `escalation_recommended`
- `source_signal_ids`
- `priority`

## Selection and Fatigue Rules

- Priority order is `support_risk` first, then `meal_guidance`, then `weight_check_in`.
- Tie-break on higher confidence first, then most recent matching signal.
- Never create a second active nudge for the same member.
- Apply a 24-hour cooldown for the same `nudge_type` after `act_now` or `dismiss`.
- Apply a daily cap of 2 auto-delivered nudges per member.
- Support-risk escalation bypasses cooldown and daily cap.
- A new signal does not replace an existing active nudge in this prototype.

## Status Model

- `active`: visible to the member and awaiting action
- `acted`: member chose `act_now`
- `dismissed`: member chose `dismiss`
- `escalated`: low-confidence path or explicit `ask_for_help`

## Implementation Notes

- Prefer straightforward evaluator functions over a generic rule framework.
- Keep confidence assignment explicit in code so it is easy to explain during review.
- Preserve the reasoning trail needed for coach visibility and audit logging later.
- Low-confidence handling should be a first-class outcome, not an error path.
- Do not let phrasing concerns influence whether a nudge is selected.
- Keep the explanation basis terse and factual so later phases can turn it into member copy or coach detail without re-deriving the decision.

## Recommended Work Breakdown

1. Define the candidate structure returned by each evaluator.
2. Implement the three evaluator functions against seeded signals and member goals.
3. Add prioritization and tie-breaking rules.
4. Add fatigue and deduplication logic.
5. Add escalation behavior for low-confidence and risk-support cases.
6. Ensure reevaluation only happens when there is no active nudge.
7. Verify repeated reads do not create duplicate active nudges.

## Acceptance Criteria

- All three assignment scenarios map to explicit evaluator behavior.
- The engine returns at most one active nudge candidate per member.
- Low-confidence cases are withheld from auto-delivery and marked for coach review.
- Repeated retrieval for the same member is idempotent when state has not changed.
- Fatigue controls prevent noisy or duplicate nudges.
- Priority and tie-break behavior are deterministic and documented in code.

## Verification

- Run the engine against each seeded member and confirm the expected outcome.
- Re-run selection for the same member and confirm no duplicate active nudge is created.
- Validate that a support-risk case prefers escalation over another automated nudge.
- Confirm evaluator output contains the fields later phases need for APIs, UI, and audit history.
- Add at least one case where multiple evaluators match and confirm the priority order wins predictably.

## Merge Checkpoint

Merge when the system can deterministically decide whether a member should receive a nudge, what it should be, and when to defer to a human.
