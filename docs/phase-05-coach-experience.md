# Phase 05: Coach Experience

## Objective

Implement the internal coach-facing view that shows what nudges the system generated, how confident it was, how members responded, and which cases need human attention.

## Suggested Branch

`phase/05-coach-experience`

## Why This Phase Exists

The assignment explicitly asks for safe escalation and coach visibility. This phase shows that automated nudging and human review are connected parts of the same workflow.

## Dependencies

- [phase-03-api-contracts.md](./phase-03-api-contracts.md)

## In Scope

- Build a coach route and page shell.
- Show recent nudges in reverse chronological order.
- Show open escalations as a distinct queue.
- Display member name, nudge type, content, explanation, matched reason, confidence, user response, and escalation recommendation.
- Display escalation reason, source, status, and created timestamp.

## Out of Scope

- Coach assignment workflows.
- Resolution workflows beyond basic visibility unless they are very cheap to add.
- Full analytics dashboards.

## Deliverables

- Coach page wired to the recent nudges and open escalations APIs.
- A recent nudges list that makes decision reasoning visible.
- An escalations queue that makes review priority obvious.
- A simple layout that works on common laptop screen sizes.

## Default Data Behavior

- Show the most recent 20 nudges by default, ordered by `created_at DESC`.
- Show open escalations ordered by `created_at DESC`.
- Keep the initial coach view read-only.
- Do not add filters unless the unfiltered page is hard to scan during manual verification.

## UX Requirements

- Confidence and matched reason must be easy to scan.
- User response should be visible without opening a detail view.
- Escalations should feel operationally distinct from standard nudges.
- Keep the page lightweight; the goal is review clarity, not workflow depth.
- Provide explicit empty states for both lists.

## Layout Sketch

```text
+-----------------------+-------------------------------+
| Open escalations      | Recent nudges                 |
| - member              | - member                      |
| - reason              | - content                     |
| - source              | - explanation                 |
| - created_at          | - matched_reason              |
|                       | - confidence + last action    |
+-----------------------+-------------------------------+
```

Suggested empty states:

- Escalations: `No open escalations right now.`
- Recent nudges: `No recent nudges yet.`

## Implementation Notes

- Build for read-only inspection first.
- Prefer sorting and grouping that surfaces urgent cases without extra controls.
- Only add filters if the page becomes hard to scan without them.
- Keep the coach view aligned with the same reasoning fields emitted by the engine and API layers.
- If filters are added, keep them to lightweight chips such as `High`, `Medium`, `Low`, or `Escalated`.

## Recommended Work Breakdown

1. Create the coach route and page structure.
2. Fetch recent nudges and open escalations.
3. Build the recent nudges feed.
4. Build the escalations queue.
5. Polish ordering, labels, and empty states.

## Acceptance Criteria

- A reviewer can see recent nudges and open escalations in one internal view.
- The view exposes the confidence or rule match behind each nudge.
- User responses are visible for recently acted or dismissed nudges.
- Escalations caused by low confidence or help requests are clearly distinguishable.
- The default view remains readable without requiring filters, modals, or drill-down navigation.

## Verification

- Confirm that the seeded history appears in recent nudges.
- Trigger `ask_for_help` from the member flow and confirm the escalation becomes visible here.
- Confirm support-risk cases show reasoning that is understandable during review.
- Verify the page remains readable without extra filtering controls.

## Merge Checkpoint

Merge when the coach workflow can reliably answer what the system did, why it did it, and where a human should intervene.
