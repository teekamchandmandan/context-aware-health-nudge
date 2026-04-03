# Phase 08: UI/UX Redesign

## Objective

Redesign the member and coach experiences into a professional, trustworthy, and production-credible interface without removing or weakening the features, safety behaviors, and demo flows already built.

## Suggested Branch

`phase/08-ui-ux-redesign`

## Why This Phase Exists

The current product slice is functionally coherent, but the interface is still implementation-first. This phase raises the quality bar on visual design, interaction design, responsiveness, and accessibility so the assignment reads as a strong product experience rather than only a working prototype.

This is a redesign phase, not a feature expansion phase. The job is to improve how the existing slice is experienced, understood, and trusted.

## Dependencies

- [phase-04-member-experience.md](./phase-04-member-experience.md)
- [phase-05-coach-experience.md](./phase-05-coach-experience.md)
- [phase-06-llm-safety-and-phrasing.md](./phase-06-llm-safety-and-phrasing.md)
- [phase-07-observability-and-audit.md](./phase-07-observability-and-audit.md)

The redesign should assume the current member flow, coach flow, phrasing behavior, and audit-aware workflow already exist and should remain intact.

## In Scope

- Introduce a cohesive visual direction across the client.
- Improve layout, spacing, typography, color use, and information hierarchy.
- Refactor repeated UI patterns into a small reusable frontend design foundation.
- Redesign the member page so the nudge loop feels calm, clear, and trustworthy.
- Redesign the coach page so escalations and recent nudges are easier to scan and review.
- Improve mobile, tablet, and common laptop responsiveness.
- Improve accessibility fundamentals including labels, focus states, keyboard behavior, and non-color status signaling.
- Improve empty, loading, success, and error states.
- Improve timestamp readability and interaction feedback.
- Keep the redesign aligned with the existing API contracts and backend behavior.

## Out of Scope

- New backend rules or confidence logic.
- New product workflows such as auth, notifications, analytics dashboards, or coach assignment tooling.
- New decision-engine scenarios beyond the existing member-to-coach slice.
- Expanding the coach page into a full operations console.
- Replacing the current data model or API surface unless a narrow documentation-backed change is unavoidable.

## Non-Negotiable Behaviors To Preserve

- Keep the two primary routes: member and coach.
- Keep the three member actions: `act_now`, `dismiss`, and `ask_for_help`.
- Keep support for logging meals, weight, and mood.
- Keep seeded member switching and the demo reset flow.
- Keep escalation visibility for coach review.
- Keep the coach experience read-only by default.
- Keep one active nudge at a time for the member flow.
- Keep existing safety boundaries, including calm language and explicit escalation behavior.
- Keep compatibility with the existing API contracts and response shapes.

## Deliverables

- A redesign brief translated into concrete page and component changes in the client.
- A shared visual and component foundation for the current product slice.
- A redesigned member experience that preserves the current live interaction loop.
- A redesigned coach experience that improves review clarity and prioritization.
- Updated loading, empty, success, escalated, and error states across both pages.
- Responsive behavior verified for mobile and laptop usage.
- Accessibility-focused polish that removes obvious baseline issues from the existing UI.

## Experience Direction

The redesigned UI should feel like a modern care product:

- calm rather than flashy
- structured rather than sparse
- trustworthy rather than promotional
- operationally clear rather than dashboard-heavy

The member experience should emphasize confidence, clarity, and immediate next steps. The coach experience should emphasize scanability, priority, and reasoning visibility.

## Member Experience Goals

- Make the active nudge the primary focus without hiding the quick-log tools.
- Create a clearer action hierarchy so the main next step is obvious.
- Improve field labeling and validation visibility in the quick-log flow.
- Make action confirmations and escalated states feel deliberate rather than abrupt.
- Preserve the immediate loop between logging a signal and seeing updated member state.
- Ensure the member page remains usable without relying on hidden detail panels or fragile layout assumptions.

## Coach Experience Goals

- Make open escalations visually and structurally distinct from recent nudges.
- Improve readability of confidence, matched reason, latest action, and phrasing source.
- Improve timestamp presentation for quick review.
- Preserve the lightweight read-only posture while making the page easier to scan.
- Make the layout effective both as stacked mobile sections and as a two-column desktop review surface.

## Frontend Foundation Requirements

- Establish a small set of reusable primitives for page shell, cards, buttons, badges, alerts, fields, and loading states.
- Reduce repeated one-off Tailwind class stacks where they obscure intent or make iteration harder.
- Keep the design system intentionally small and driven by the needs of the current product slice.
- Prefer consistent tokens and reusable layout patterns over page-specific styling drift.

## UX and Accessibility Requirements

- All inputs should have clear visible labels.
- Tab-like controls should be keyboard reachable and predictable.
- Status and confidence cues should not rely on color alone.
- Focus states should remain obvious across all key interactions.
- Loading states should communicate progress without freezing the page.
- Error states should be retryable and understandable.
- Success states should confirm what happened without requiring guesswork.

## Recommended Work Breakdown

1. Define the redesign guardrails and reusable visual foundation.
2. Rework shared layout and primitive UI patterns.
3. Redesign the member page and nudge interaction flow.
4. Redesign the coach page and review layout.
5. Refine responsive behavior, state handling, and accessibility.
6. Validate all seeded scenarios against the redesigned experience.

## Acceptance Criteria

- The redesigned UI looks materially more polished and professional than the current baseline.
- No existing member or coach feature required by earlier phases is lost.
- The member flow remains centered on one active nudge and three explicit actions.
- Signal logging remains lightweight and usable.
- The coach view remains readable without adding heavy workflow surface area.
- The redesigned experience works cleanly on both mobile and laptop widths.
- The UI handles loading, empty, success, escalated, and error states clearly.
- The redesign does not require backend rule changes to function.

## Verification

- Walk through all seeded member scenarios in the redesigned member route.
- Submit fresh meal, weight, and mood signals and confirm the interaction loop still works.
- Trigger all three nudge actions and verify the resulting UI states.
- Verify `ask_for_help` still produces visible member confirmation and coach visibility.
- Review both pages at mobile and laptop sizes.
- Smoke test keyboard reachability, visible focus, and labeled form controls.

## Merge Checkpoint

Merge when the product remains functionally equivalent to the earlier phases but the UI/UX quality is clearly upgraded and ready for final delivery validation.
