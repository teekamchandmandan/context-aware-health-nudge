# Product and Technical Note

_(For setup instructions and the architecture overview, see the [README](README.md).)_

## What This Solves

This prototype implements a signal-driven feature where recent member inputs—meals, weight logs, mood entries—drive a contextual next step before the member has to interpret their own history or a coach has to manually inspect raw data.

It focuses on four concrete cases:

- A member on a low-carb program logs a higher-carb meal and gets a dinner suggestion while the meal is still recent.
- A member stops logging weight for several days and gets a check-in reminder.
- A member reports low mood after repeatedly dismissing nudges and is escalated to a coach instead of receiving another automated message.
- A member logs low mood three or more times in a short window and is escalated to a coach based on the pattern alone, even without any dismissed nudges.

The design focuses on presenting just one current recommendation, explaining why it appeared, and giving the member a clear choice to act, dismiss, or ask for help.

## Assumptions

This note assumes a narrow, local prototype rather than a production health platform.

- **Simulated data.** All member profiles and signals are seeded or entered through the UI. No real health data sources are connected.
- **No authentication.** Member switching is handled via a query parameter. A production system would require identity, consent, and access controls.
- **Local persistence.** SQLite is used as the data store. A production deployment would use a managed relational database.
- **Deterministic decisioning.** The system decides whether to show a nudge through explicit rules, not through an LLM.
- **Bounded LLM usage.** OpenAI is used only to classify meal photos and rewrite approved nudge copy. If the model is unavailable or returns invalid output, the system falls back to deterministic defaults.
- **Single nudge at a time.** The product shows one _active_ nudge per member instead of a queue (though superseded nudges accumulate in history when new signals arrive). That keeps the experience focused and makes the prototype easier to evaluate.
- **Limited coach surface.** The coach view exposes recent nudges and open escalations for review and supports resolving escalations. Assignment and note-taking are not supported.

## System Model

The runtime model uses straightforward evaluation logic. Member inputs (meals, weight, mood, sleep) are stored as signals—timestamped records in the `signals` table. The engine checks those signals against four deterministic rules. If more than one rule matches, the system picks one current state based on priority. Non-urgent nudges respect a 24-hour cooldown per nudge type and a daily cap of 2 auto-delivered nudges. The support-risk path bypasses those limits because a possible need for human follow-up matters more than avoiding one extra prompt.

- **Meal guidance.** Triggered when a member with a low-carb dietary goal (stored as `goal_type` on their profile) logs a recent meal classified as higher carb. The system responds with an active nudge for the next meal.
- **Weight check-in.** Triggered when a member has not logged weight in the last 4 days. The system responds with an active reminder.
- **Support risk (dismiss-based).** Triggered when a member reports low mood and has dismissed at least 2 nudges in the last 7 days. The system responds with an escalated state for coach review instead of another automated nudge.
- **Support risk (repeated low mood).** Triggered when a member logs low mood 3 or more times within the last 3 days, independent of dismiss history. The system escalates to a coach based on the mood pattern alone.

Both support-risk paths produce the same `support_risk` nudge type and route to the same escalation flow.

Confidence is a 0–1 score computed from observable factors—signal recency, severity, recent member activity—rather than assigned by hand. Nudges with confidence at or above 0.50 are delivered directly to the member; nudges below 0.50, or any nudge flagged as safety-sensitive, are escalated to a coach. Meal guidance gets stronger when the meal is recent and clearly classified. Weight check-in starts lower because absence of data is a weaker signal, then rises as the member becomes more overdue. Support risk is hard-capped below 0.48 by design, so it always routes to coach review rather than acting like a high-confidence automated recommendation.

The system also checks freshness on every member read. If a new signal arrives after a nudge is created, the older nudge is retired and the member is re-evaluated. That keeps the surface current instead of showing stale guidance.

Audit events record nudge generation, user actions, escalation creation, and LLM calls or fallbacks in the `audit_events` table so the behavior stays reviewable. These events are also accessible through the coach API endpoints and can be queried directly in SQLite.

## Success Metrics

For a production deployment, the following metrics would provide visibility into the system:

**Engagement**

- **Nudge act-on rate.** Percentage of active nudges where the member selects "I will do this."
- **Signal logging frequency.** Whether members log more signals after receiving relevant nudges.

**Quality**

- **Dismissal rate by nudge type.** High dismissal of a specific type suggests the rule is too aggressive or the phrasing is unhelpful.
- **Escalation-to-resolution time** _(not yet measurable)_**.** How quickly a coach reviews and responds to an open escalation.

**Safety**

- **False-positive escalation rate** _(not yet measurable)_**.** Percentage of escalations that the coach determines did not require human follow-up.
- **LLM fallback rate by surface.** How often phrasing or meal analysis falls back to deterministic defaults, and whether fallback correlates with lower act-on rates.

In the current repo, a few of these metrics are partially visible now: act-on rate, dismissal rate, fallback rate, and basic escalation volume. Signal logging frequency is visible in the data but not yet summarized as product analytics. Escalation-to-resolution time and false-positive escalation rate are not yet measurable in a useful way because the coach workflow does not support resolution or triage feedback.

## Major Risks and Mitigations

### Over-nudging and fatigue

**Risk:** Members receive too many nudges and begin ignoring or dismissing them, reducing trust in the system.

**Mitigation:** The engine enforces a 24-hour cooldown per nudge type after a member selects `act_now` or `dismiss`, plus a daily cap of 2 auto-delivered nudges. Support-risk bypasses these limits because under-nudging in a safety-relevant case is a worse outcome than a single extra notification.

### LLM phrasing producing unsafe content

**Risk:** The LLM generates text that includes medical advice, diagnoses, or prescriptive language that a wellness nudge should not contain.

**Mitigation:** The system validates LLM output against a blocked-term list (diagnose, medication, prescription, treatment plan, etc.), caps each field at 160 characters, and falls back to a deterministic template on timeout, provider error, missing keys, invalid JSON, or validation failure. The prompt is tightly scoped to structured facts and explicitly prohibits medical framing. Audit events record whether each nudge used LLM or template phrasing.

### False-positive escalations

**Risk:** The support-risk evaluator flags a member for coach review when no real concern exists, wasting coach attention and potentially alarming the member.

**Mitigation:** The escalation rule is deliberately conservative. The dismiss-based path requires both a low-mood signal within 3 days and at least 2 dismissed nudges within 7 days. The repeated-low-mood path requires 3 or more low-mood signals within 3 days, catching persistent distress even without dismiss history. Both paths use confidence scores hard-capped below the automation threshold so they always route to a coach. The member-facing message simply says that the care team has been notified. The coach view shows the matched reason and confidence score for quick triage.

### Stale nudge persistence

**Risk:** A member sees an outdated nudge because the system does not re-evaluate after new signals arrive.

**Mitigation:** On every read, the engine checks whether a newer signal exists. If it does, the prior active nudge is retired and the member is re-evaluated immediately. That keeps the displayed state aligned with the latest context.

### Single-point-of-failure on LLM provider

**Risk:** If the OpenAI API is unavailable, the member experience degrades.

**Mitigation:** LLM usage is optional at every integration point. The system works with or without an API key. Template phrasing and conservative meal-analysis fallbacks ensure the core flow is never blocked by an external dependency.

## Rollout Plan

For a broader deployment, a phased rollout approach introduces changes gradually:

### Stage 1 - Internal review

- Run the system with synthetic or replayed data and review every generated nudge and escalation with a coach or program lead.
- Validate engine behavior, API contracts, and audit recording against the existing automated test suite before manual review.
- Use audit events to inspect matched reason, confidence factors, phrasing source, and escalation path rather than judging only the UI output.
- Use this stage to tune thresholds, validate phrasing safety, and confirm that the escalation rule is not too noisy.

### Stage 2 - Limited pilot

- Enable the workflow for a small opted-in cohort in one program.
- Keep coach review in the loop for every escalation and sample a portion of member-visible nudges.
- Watch act-on rate, dismissal rate by nudge type, fallback rate, and escalation volume before broadening scope. Use those signals to tune the existing rules before adding new evaluator types.
- Once the baseline flow is stable, run small A/B tests on low-risk variables such as phrasing and explanation copy. A/B testing for escalation behavior or safety routing should be avoided until the review process is broadly validated.

### Stage 3 - Broader rollout

- Add the missing operational pieces before wider rollout: authentication, coach resolution workflow, configurable thresholds, and a basic metrics dashboard.
- Replace SQLite with a managed relational store and add role-aware access controls before treating the prototype as shared operational software.
- Expand to additional programs only after the rules have been tuned on real usage and the coach workflow can absorb the escalation volume.
- Add new evaluator types only after the initial four flows are stable and reviewable.

## Summary

This prototype covers four nudge rules: meal guidance, weight check-in, dismiss-based support risk, and repeated-low-mood support risk. A confidence model routes uncertain or safety-sensitive cases to a coach. Fatigue controls enforce cooldowns and a daily cap to prevent over-nudging. An audit trail records every decision so the behavior stays reviewable. The rollout plan moves from internal review through limited pilot to broader deployment, with each step conditioned on observed metrics. The system works fully without an LLM and is designed to be extended with new evaluator types once the initial rules are validated.
