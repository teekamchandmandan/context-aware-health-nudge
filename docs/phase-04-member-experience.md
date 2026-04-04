# Phase 04: Member Experience

## Objective

Implement the member-facing flow that shows one personalized nudge, explains why it appeared, lets the member act now, dismiss, or ask for help, and allows lightweight logging of fresh member signals.

## Suggested Branch

`phase/04-member-experience`

## Why This Phase Exists

This is the primary assignment experience. It should feel clear and trustworthy without adding unnecessary product breadth.

This route is distinct from the coach experience and should remain member-only in both content and navigation.

## Dependencies

- [phase-03-api-contracts.md](./phase-03-api-contracts.md)
- The Vite + React + TypeScript + Tailwind CSS scaffold in `client/` was established in Phase 01. No client setup step is needed.

## In Scope

- Build the member route and page shell.
- Fetch and display the current active nudge.
- Add compact controls for logging weight, mood, and meal updates.
- Show the nudge content and a short explanation for why it appeared.
- Provide the three required actions: act now, dismiss, and ask for help.
- Handle loading, empty, success, and error states.
- Support basic member switching for demo purposes if needed because auth is out of scope.

## Out of Scope

- Auth.
- Notification channels beyond the single page experience.
- Broad dashboard or profile management features.

## Deliverables

- Member page wired to the nudge API.
- Member page wired to the signal intake API for live input.
- A nudge card component or equivalent view structure.
- Action handling that updates the UI based on backend responses.
- Empty state for members who do not currently need a nudge.
- A simple demo path for reviewing the three demo scenarios.

## Route and Demo Convention

- Use a single member route such as `/member?memberId=member_meal_01`.
- Provide a lightweight seeded-member switcher at the top of the page so reviewers can move between scenarios without auth.
- Default to the meal scenario member on first load.
- Make it easy to trigger or resolve at least one scenario through fresh member input instead of relying only on seeded outcomes.
- Keep the member route visually and behaviorally separate from the coach route; do not add direct in-product links from the member page into coach review.

## UX Requirements

- Keep the page focused on one active nudge.
- Strengthen the information hierarchy so the active nudge is the dominant focal surface and quick logging remains supportive rather than competitive.
- Keep signal logging lightweight and adjacent to the nudge card rather than turning the page into a broad dashboard.
- Use plain, calm language that avoids diagnosis or overclaiming.
- Make the explanation legible and visibly separate from the main recommendation.
- Reflect action results immediately so the user is not left uncertain about what happened.
- Prefer a centered card layout with the recommendation, explanation, and three actions visible without scrolling on a laptop.
- Provide a reliable structured fallback for meal logging even if photo capture is available.
- Do not surface coach-only controls, coach-facing reasoning details, or direct coach navigation in the member route.

## Design Adaptation Note

The redesign pass may use the Stitch screen `Member Dashboard - Desktop` (`88190d7e686247f8b74d1a88f9791d90`) from project `18374012017328105154` as a guiding layout reference. Adapt the visual direction to this product's single-nudge flow rather than copying the source literally.

## Required UI States

- `loading`: a small non-blocking loading state while the active nudge is fetched
- `active`: nudge card with content, explanation, and three actions
- `no_nudge`: clear message that there is no recommendation right now
- `escalated`: calm message that support has been flagged for coach review
- `error`: retryable fetch or action failure state

Suggested state copy is intentionally simple:

- `no_nudge`: `No action needed right now. Check back later after you log your next update.`
- `escalated`: `We have flagged this for coach review instead of showing an automated suggestion.`
- `error`: `We could not load your nudge. Please try again.`

## Layout Sketch

```text
+--------------------------------------------------+
| Member selector                                  |
|                                                  |
| Quick log an update                              |
| - weight input                                   |
| - mood toggle + optional note                    |
| - structured meal entry                          |
|                                                  |
|  Personalized nudge card                         |
|  - content                                       |
|  - Why am I seeing this? explanation             |
|  - confidence is not shown to the member         |
|                                                  |
|  [Act now] [Dismiss] [Ask for help]              |
+--------------------------------------------------+
```

## Implementation Notes

- Do not overbuild state management for a single-page flow.
- Design for trust and clarity over visual complexity.
- The page should be usable with deterministic template phrasing before LLM polish lands.
- Keep signal submission and nudge action handling on the same page so the interaction loop feels immediate.
- Keep the member flow resilient to empty or low-confidence states returned by the backend.
- The shipped Phase 04 flow uses structured meal entry only; photo capture remains optional future scope as long as the structured path stays available.
- Prefer server-confirmed actions over optimistic updates because trust matters more than speed in this flow.
- Seeded member switching is allowed for the demo, but cross-view shortcuts between member and coach should not be part of the intended member UX.

## Recommended Work Breakdown

1. Create the member route and page structure.
2. Add data fetching for the active nudge.
3. Add signal logging controls for weight, mood, and meals.
4. Build the nudge card and explanation presentation.
5. Wire the three actions to the action endpoint.
6. Add empty, loading, and error states.
7. Verify the three demo scenarios and at least one fresh input path manually.

## Acceptance Criteria

- The member page shows at most one active nudge at a time.
- A reviewer can log at least one new signal and see the member state update from live interaction.
- The explanation for why the nudge appeared is visible and understandable.
- All three required actions work end to end.
- The UI handles no-nudge and error states gracefully.
- A reviewer can exercise each seeded scenario without auth.
- Demo member switching is visible and does not require editing the URL manually.
- Meal logging remains usable through structured inputs even if photo capture is unavailable.

## Verification

- Load the member page for each seeded member and confirm the expected state.
- Submit a fresh weight, mood, or meal signal and confirm the next nudge fetch reflects the new context.
- Trigger each action type and confirm the page updates correctly.
- Verify `ask_for_help` produces a visible confirmation even before coach review is opened.
- Confirm the member UI does not expose a direct navigation path into the coach route.
- Confirm no extra product surface has been added beyond the required member flow.
- Confirm the page still works correctly for `state: "escalated"` with no visible nudge card.

## Merge Checkpoint

Merge when the core member journey is demoable end to end against the real API.
