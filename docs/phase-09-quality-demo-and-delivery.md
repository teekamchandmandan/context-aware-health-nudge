# Phase 09: Quality, Demo, and Delivery

## Objective

Close the loop on the assignment by adding focused tests, validating the end-to-end demo flow, and completing the written deliverables.

## Suggested Branch

`phase/09-quality-demo-and-delivery`

## Why This Phase Exists

The last branch should improve trust and submission quality rather than broaden scope. It should prove that the vertical slice works, the redesigned UX holds up in practice, and the repository is documented clearly.

## Dependencies

- [phase-01-foundation-and-data.md](./phase-01-foundation-and-data.md)
- [phase-02-decision-engine.md](./phase-02-decision-engine.md)
- [phase-03-api-contracts.md](./phase-03-api-contracts.md)
- [phase-04-member-experience.md](./phase-04-member-experience.md)
- [phase-05-coach-experience.md](./phase-05-coach-experience.md)
- [phase-06-llm-safety-and-phrasing.md](./phase-06-llm-safety-and-phrasing.md)
- [phase-07-observability-and-audit.md](./phase-07-observability-and-audit.md)
- [phase-08-ui-ux-redesign.md](./phase-08-ui-ux-redesign.md)

For the full intended submission, assume all prior phases are complete. If a branch is tested in isolation, document the missing dependencies explicitly instead of mocking hidden behavior.

## In Scope

- Add focused automated tests for the most trust-sensitive backend behavior.
- Run a manual walkthrough across the three scenarios using both seeded starting context and live member-submitted signals.
- Finalize README setup and architecture guidance based on the actual implementation.
- Write the 1-2 page product and technical note required by the assignment.
- Add an explicit AI usage disclosure covering tools and boundaries.
- Verify that the redesigned UI from Phase 08 remains coherent, responsive, and demoable across the core flows.

## Out of Scope

- Large feature additions.
- Production hardening beyond what is needed for a coherent demo.
- Broad refactors that change earlier branch intent without clear payoff.

## Deliverables

- Automated backend tests for core decisioning and fallback behavior.
- A manual verification checklist for member and coach flows, including live signal capture.
- Updated README with real setup and run instructions.
- Product and technical note covering user problem, assumptions, metrics, risks, and rollout.
- Clear AI disclosure matching the actual workflow used.

## Quality Defaults

- Prefer `pytest` for backend tests.
- Focus on explicit rule-path coverage rather than a vanity repo-wide coverage target.
- Store the final product and technical note in `docs/product-technical-note.md`.
- Store the manual verification checklist in `docs/manual-verification.md` or as a clearly labeled README appendix.

## Product Note Checklist

The required 1-2 page note should explicitly cover:

- user problem and why context-aware nudges matter
- assumptions made because real health integrations are out of scope
- success metrics for engagement, quality, and safety
- major risks and mitigations
- rollout plan for a limited pilot

## AI Disclosure Checklist

The final disclosure should state:

- which AI tools were used
- which artifacts they helped draft or implement
- which decisions were manually reviewed
- how deterministic fallbacks and safety boundaries were evaluated

## Test Focus

- Meal mismatch produces the expected nudge.
- Missing weight log produces the expected reminder.
- Support-risk cases escalate correctly.
- No matching signals produces no nudge.
- `ask_for_help` creates an escalation.
- Active nudge retrieval is idempotent.
- Signal submission affects later nudge retrieval without creating duplicate active nudges.
- LLM failure falls back to templates.

## Implementation Notes

- Resist expanding scope late in the project.
- Keep the demo honest: at least one meaningful member-facing state change should come from a fresh weight, mood, or meal log rather than a fully pre-seeded state.
- If a gap is too large to finish well, document it rather than disguising it.
- Keep the README reviewer-oriented and fast to run.
- The product note should describe the system that exists, not a larger imagined platform.
- Manual verification should cover at least one pass through each seeded scenario, one explicit fallback case, and one pass through the redesigned member and coach surfaces.

## Recommended Work Breakdown

1. Add the core automated tests.
2. Run manual walkthroughs for the seeded starting contexts and live input paths.
3. Verify the redesigned UI across the required member and coach states.
4. Update README with exact local setup instructions.
5. Write the product and technical note.
6. Add the final AI usage disclosure.

## Acceptance Criteria

- The most important backend behavior is covered by focused tests.
- A reviewer can run the project locally using the README alone.
- A reviewer can trigger at least one nudge or resolution through live member input after reset.
- The redesigned member and coach surfaces remain coherent during end-to-end walkthroughs.
- The submission includes the required product and technical note.
- AI usage is disclosed clearly and accurately.
- The final repo remains a coherent end-to-end vertical slice.
- Verification artifacts have an obvious home in the repo instead of living only in ad hoc notes.

## Verification

- Run the automated test suite.
- Walk through each scenario from member view to coach visibility, including at least one fresh signal submission.
- Review the redesigned member and coach flows from a clean-start perspective across desktop and mobile widths.
- Review the README from a clean-start perspective and remove any missing steps.
- Confirm all assignment deliverables are present in the repository.

## Merge Checkpoint

Merge when the repository is ready to hand to a reviewer without verbal explanation.
