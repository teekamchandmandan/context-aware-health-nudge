# Phase 07: Observability and Audit

## Objective

Add the persisted audit trail and structured logging needed to understand nudge quality, user behavior, escalation decisions, and AI fallback events.

## Suggested Branch

`phase/07-observability-and-audit`

## Why This Phase Exists

The assignment asks for logging that supports performance, quality, and safety. This phase makes system behavior reviewable without turning the prototype into an analytics platform.

## Dependencies

- [phase-03-api-contracts.md](./phase-03-api-contracts.md)
- [phase-06-llm-safety-and-phrasing.md](./phase-06-llm-safety-and-phrasing.md)

## In Scope

- Persist key audit events.
- Add structured backend logs for important workflow transitions.
- Record whether phrasing came from the LLM or fallback templates.
- Make enough history available that the coach flow and product note can speak credibly about safety and quality.

## Out of Scope

- A full analytics dashboard.
- External observability vendors.
- Alerting or incident management systems.

## Deliverables

- Audit event writes for `nudge_generated`, `user_action`, `escalation_created`, `llm_call`, and `llm_fallback`.
- Structured logs containing member ID, nudge ID, matched reason, confidence, escalation decision, and phrasing source.
- Clear conventions for what belongs in audit tables versus ephemeral application logs.

## Audit Payload Expectations

Each event should store a compact JSON payload with only the fields needed for review.

| Event type           | Minimum payload fields                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| `nudge_generated`    | `member_id`, `nudge_id`, `nudge_type`, `matched_reason`, `confidence`, `phrasing_source` |
| `user_action`        | `member_id`, `nudge_id`, `action_type`, `previous_status`, `new_status`                  |
| `escalation_created` | `member_id`, `nudge_id`, `reason`, `source`, `status`                                    |
| `llm_call`           | `member_id`, `nudge_type`, `provider`, `success`, `latency_ms`                           |
| `llm_fallback`       | `member_id`, `nudge_type`, `fallback_reason`                                             |

## Logging Defaults

- Emit structured JSON logs to stdout for local development.
- Use `INFO` for lifecycle events and `WARNING` for fallback or validation failures.
- Keep audit rows in SQLite for the lifetime of the local database.
- Do not add file rotation or external sinks in this assignment unless needed for a local demo.

## Useful Review Metrics

- Nudge generation count by `nudge_type`
- Dismiss rate by `nudge_type`
- `ask_for_help` rate
- Escalation count
- LLM fallback rate
- Median LLM latency if AI phrasing is enabled

## Logging Model

- Audit events should capture durable product history.
- Structured application logs should capture runtime behavior useful during local review and debugging.
- Avoid duplicating sensitive or noisy payloads when summary fields are enough.
- Coach pages should continue to read from nudge and escalation records; audit events are primarily for backend review in this prototype.

## Implementation Notes

- Keep event names stable and easy to query.
- Prefer concise payloads that are meaningful during demo review.
- Add observability where decisions happen, not as a separate afterthought layer.
- Preserve enough context that the final technical note can reference actual system instrumentation.

## Recommended Work Breakdown

1. Implement durable audit writes for core lifecycle events.
2. Add structured logging around decisioning and action handling.
3. Add LLM source logging and fallback logging.
4. Verify the coach view and manual review flow still read clearly with the added data.

## Acceptance Criteria

- Core lifecycle events are persisted consistently.
- Logs make it possible to reconstruct why a nudge was created and what happened next.
- AI success and fallback cases are distinguishable.
- The added instrumentation supports safety review without requiring a full analytics product.
- Audit payloads remain compact enough to inspect manually during demo review.

## Verification

- Generate a nudge, take each action type, and confirm the corresponding audit records exist.
- Trigger an LLM fallback and confirm it is logged distinctly.
- Review logs for enough detail to debug decision outcomes without overwhelming noise.
- Confirm the system still behaves correctly if logging is present but no external tooling is configured.

## Merge Checkpoint

Merge when the prototype has a credible observability story that supports product quality and safety review.
