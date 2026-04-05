# Product and Technical Note

## User Problem

This prototype is built around three concrete cases:

- A low-carb member logs a higher-carb meal and gets a dinner suggestion while the meal is still recent.
- A member stops logging weight for several days and gets a check-in reminder.
- A member reports low mood after repeatedly dismissing nudges and is escalated to a coach instead of receiving another automated message.

The product question is whether recent signals can drive one practical next step without asking the member to interpret their own history or the coach to inspect raw events. The design choice in this prototype is to show one current recommendation, explain why it appeared, and give the member a clear out: act, dismiss, or ask for help.

## Assumptions

Assumptions and scope constraints:

- **Simulated data.** All member profiles and signals are seeded or entered through the UI. No real health data sources are connected.
- **No authentication.** Member switching is handled via a query parameter. A production system would require identity, consent, and access controls.
- **Local persistence.** SQLite is used as the data store. A production deployment would use a managed relational database.
- **Bounded LLM usage.** OpenAI is used only for phrasing nudge text and analysing meal photos. The decision engine is entirely deterministic. LLM phrasing is optional — the system degrades gracefully to static templates when no API key is configured, or when the LLM times out, returns invalid JSON, or produces content containing blocked medical terms.
- **Single nudge at a time.** The system presents one nudge per member at a time. A production version might surface a prioritised queue, but the single-nudge constraint keeps the member experience focused and testable.
- **Read-only coach surface.** The coach view exposes recent nudges and open escalations for review but does not support assignment, resolution, or note-taking workflows.

## Success Metrics

If this moved beyond a local prototype, I would track:

| Category | Metric | Signal |
|----------|--------|--------|
| **Engagement** | Nudge act-on rate | Percentage of active nudges where the member selects "I will do this" |
| **Engagement** | Signal logging frequency | Whether members log more signals after receiving relevant nudges |
| **Quality** | Dismissal rate by nudge type | High dismissal of a specific type suggests the rule is too aggressive or the phrasing is unhelpful |
| **Quality** | Escalation-to-resolution time | How quickly a coach reviews and responds to an open escalation |
| **Safety** | False-positive escalation rate | Percentage of escalations that the coach determines did not require human follow-up |
| **Safety** | LLM fallback rate | How often phrasing falls back to templates, and whether fallback correlates with lower act-on rates |

In this repo, these metrics are only partially observable through `audit_events` and the coach view; there is no dedicated analytics surface yet.

## Major Risks and Mitigations

### Over-nudging and fatigue

**Risk:** Members receive too many nudges and begin ignoring or dismissing them, reducing trust in the system.

**Mitigation:** The engine enforces a 24-hour cooldown per nudge type after a member selects `act_now` or `dismiss`, plus a daily cap of 2 auto-delivered nudges. Support-risk bypasses these limits because under-nudging in a safety-relevant case is a worse outcome than a single extra notification.

### LLM phrasing producing unsafe content

**Risk:** The LLM generates text that includes medical advice, diagnoses, or prescriptive language that a wellness nudge should not contain.

**Mitigation:** LLM output is validated against a blocked-term list (diagnose, medication, prescription, treatment plan, etc.), capped at 160 characters per field, and rejected in favour of a deterministic template on any validation failure. The LLM prompt is tightly scoped to structured facts and explicitly prohibits medical framing. Audit events record whether each nudge used LLM or template phrasing, making review straightforward.

### False-positive escalations

**Risk:** The support-risk evaluator flags a member for coach review when no real concern exists, wasting coach attention and potentially alarming the member.

**Mitigation:** The escalation threshold is deliberately conservative — it requires both a low-mood signal within 3 days and at least 2 dismissed nudges within 7 days. The member-facing experience simply states that the care team has been notified, without dramatising the reason. The coach view shows the matched reason and confidence score so the coach can triage quickly.

### Stale nudge persistence

**Risk:** A member sees an outdated nudge because the system does not re-evaluate after new signals arrive.

**Mitigation:** The engine checks whether any signal is newer than the current active nudge on every read. If a newer signal exists, the prior nudge is marked `superseded` and the member is re-evaluated, ensuring the displayed nudge reflects the most recent context.

### Single-point-of-failure on LLM provider

**Risk:** If the OpenAI API is unavailable, the member experience degrades.

**Mitigation:** LLM usage is optional at every integration point. The system works identically with or without an API key. Template phrasing and conservative meal analysis fallbacks ensure the core flow is never blocked by an external dependency.

## Rollout Plan

If this moved past the local prototype, I would roll it out in three steps.

### Stage 1 - Internal review

- Run the system with synthetic or replayed data and review every generated nudge and escalation with a coach or program lead.
- Use this stage to tune evaluator thresholds, validate phrasing safety, and confirm the escalation rule is not too noisy.
- Keep the focus on failure modes: bad phrasing, stale nudges, and false-positive escalations.

### Stage 2 - Limited pilot

- Enable the workflow for a small opted-in cohort in one program.
- Keep coach review in the loop for escalations and sample a portion of member-visible nudges.
- Watch act-on rate, dismissal rate, fallback rate, and the volume of coach escalations before broadening scope.

### Stage 3 - Broader rollout

- Add the missing operational pieces before wider rollout: authentication, coach resolution workflow, configurable thresholds, and a basic metrics dashboard.
- Expand to additional programs only after the rules have been tuned on real usage and the coach workflow can absorb the escalation volume.
- Add new evaluator types only after the initial three flows are stable and reviewable.

I would not set hard numeric launch gates from this prototype alone. The value here is in defining the review process, the safety checks, and the metrics to watch once real usage begins.
