# Phase 06: LLM Safety and Phrasing

## Objective

Add bounded LLM-assisted phrasing after deterministic nudge selection, with clear fallback behavior and safety guardrails suitable for a health-adjacent product slice.

## Suggested Branch

`phase/06-llm-safety-and-phrasing`

## Why This Phase Exists

The assignment allows LLM usage, but the implementation should show restraint. This phase improves phrasing quality without letting the model decide whether a nudge should exist.

## Dependencies

- [phase-02-decision-engine.md](./phase-02-decision-engine.md)
- [phase-03-api-contracts.md](./phase-03-api-contracts.md)

## In Scope

- Add optional LLM phrasing when `OPENAI_API_KEY` is configured.
- Keep decision ownership in deterministic rules.
- Apply LLM phrasing only to newly created member-visible active nudges.
- Add template fallback for missing key, timeout, provider error, or validation failure.
- Add guardrails that reject unsafe wording.
- Log whether final phrasing came from the LLM or fallback templates.

## Out of Scope

- LLM-driven decisioning.
- Re-phrasing existing active nudges on repeated reads.
- Multi-turn conversations.
- Retrieval pipelines or external health data sources.

## Deliverables

- A phrasing service that accepts a preselected nudge candidate and returns safe copy.
- Template-based fallback phrasing for each nudge type.
- Prompt instructions that forbid diagnosis, medication advice, and treatment claims.
- Timeout and failure handling that never blocks the product flow.
- Model-aware logging that records which provider model handled each phrasing or meal-analysis attempt.

## Default Templates

- `meal_guidance`
  - Content: `Try a lighter, lower-carb dinner to balance today's earlier meal.`
  - Explanation: `You logged a higher-carb meal today and your goal is low carb.`
- `weight_check_in`
  - Content: `Take a quick weight check-in when you have a minute.`
  - Explanation: `You have not logged weight in the last few days.`
- `support_risk`
  - Content: `A coach follow-up is a better next step than another automated nudge.`
  - Explanation: `Recent signals suggest you may benefit from direct support.`

## Prompt Boundary

The phrasing prompt should receive only the already-decided nudge type, member goal, short matched reason, short explanation basis, and desired tone. Do not send raw signal history, raw image data, or other free-form member input unless they are first reduced to a short structured summary.

The meal-analysis feature should stay outside the phrasing step: the meal-analysis request may use raw image input to produce a structured meal profile, but the phrasing prompt should still receive only the structured meal details already saved on the signal.

Prompt expectations:

- Phrasing must return exactly one JSON object with only `content` and `explanation`.
- Phrasing may rewrite wording, but it may not add new health reasoning, diagnoses, warnings, or facts not present in the structured input.
- Meal analysis must return exactly one JSON object with only `meal_profile` and optional `visible_food_summary`, and should prefer `meal_profile = "unclear"` when visual evidence is weak.

Suggested system prompt shape:

```text
You rewrite an already approved wellness nudge using only the structured facts you are given.
Do not change the underlying decision, add new risks, or add medical framing.
Return exactly one JSON object with only content and explanation.
```

## Validation Rules

- Request timeout: 3 seconds.
- Reject output if `content` exceeds 160 characters.
- Reject output if `explanation` exceeds 160 characters.
- Reject output containing blocked terms such as `diagnose`, `diagnosis`, `medication`, `prescription`, `dose`, `treatment plan`, `medical advice`, `doctor`, `clinician`, or `therapy`.
- On any validation or provider failure, return deterministic templates.

## Safety Requirements

- The LLM receives only the minimum structured context needed for phrasing.
- Output must stay short, practical, and non-diagnostic.
- The photo-only meal flow must degrade cleanly to deterministic structured inputs without blocking the member experience.
- Detailed meal explanations should only reference the persisted `meal_profile` and any optional `visible_food_summary` that was saved from the meal signal.
- Any failed validation should route to deterministic templates.
- The system should remain fully usable without an API key.
- The phrasing source should be visible to backend logs and audit events as `template` or `llm`.
- LLM audit events should record `prompt_area` and `model_name` so phrasing and meal-analysis calls can be reviewed separately.
- Support-risk escalations should remain deterministic and should not introduce member-visible LLM phrasing.

## Implementation Notes

- Keep prompts simple and reviewable.
- Validate output length and disallowed phrases before persisting or returning it.
- Avoid adding heavy abstraction for a single-provider prototype.
- Make the fallback path easy to test.
- Keep phrasing source separate from `generated_by`; decision ownership remains `rule_engine`.
- Persist template copy first and only upgrade to `phrasing_source = llm` after a provider response passes validation.
- Repeated `GET /nudge` reads should return the stored active nudge without triggering another provider call.

## Recommended Work Breakdown

1. Define template phrasing for each nudge type.
2. Add the optional provider integration.
3. Add prompt boundaries and output validation.
4. Add timeout and provider-failure fallback behavior.
5. Log whether the final phrasing used the LLM or templates.

## Acceptance Criteria

- The system behaves correctly with and without an API key.
- LLM phrasing never changes the underlying decision, confidence, or escalation behavior.
- Unsafe or malformed output is rejected and replaced with deterministic templates.
- Failures do not break the member or coach flows.
- The same templates are available as the default local-development path when no API key is configured.

## Verification

- Run the system with no API key and confirm template-only behavior.
- Simulate provider failure or timeout and confirm graceful fallback.
- Review prompt and validation logic for obvious health-safety gaps.
- Confirm coach and audit views can still see whether the phrasing source was AI or fallback.
- Confirm repeated reads of an existing active nudge do not trigger another provider call.
- Confirm support-risk still returns `state: "escalated"` and remains coach-facing.

## Merge Checkpoint

Merge when AI-enhanced phrasing is optional, safe, and clearly secondary to deterministic product logic.
