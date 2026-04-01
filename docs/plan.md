# Final Plan: Context-Aware Health Nudge

## 1. Goal

This project will deliver a focused end-to-end vertical slice for the Digbi Health assignment. The goal is to show sound product judgment and clean execution through a single workflow that covers personalized nudges, explicit confidence handling, safe escalation to a coach, coach visibility, auditability, and responsible LLM usage.

The scope is intentionally narrow. This should read as a coherent product slice, not as the first draft of a generalized health platform.

---

## 2. Scope

The implementation will stay tightly bounded around one complete member-to-coach workflow.

| In scope                                              | Out of scope                  |
| ----------------------------------------------------- | ----------------------------- |
| One active nudge per member with explanation          | Auth, multi-channel delivery  |
| Three actions: act now, dismiss, ask for help         | Real health data integrations |
| Escalation to coach on low confidence or ask-for-help | Coach assignment workflows    |
| Coach view with recent nudges and open escalations    | Analytics dashboards          |
| LLM-enhanced phrasing with deterministic fallback     | ML-based confidence scoring   |
| Audit trail for key system events                     | Compliance-grade infra        |
| SQLite, local setup, no Docker                        | Configurable rules UI         |

This keeps the project small enough to finish well while still demonstrating full-stack thinking.

---

## 3. Architecture

```text
React SPA (Vite + Tailwind)        FastAPI Backend              SQLite
├── Member view                    ├── Context loading          ├── members
└── Coach view                     ├── Decision engine          ├── signals
    │                              ├── LLM phrasing layer       ├── nudges
    │    GET/POST /api/*           ├── Nudge lifecycle          ├── nudge_actions
    └──────────────────────────────├── Coach APIs               ├── escalations
                                   └── Audit logging            └── audit_events
```

The frontend will use Vite, React, React Router, and Tailwind CSS. A strict SPA keeps the interaction model simple and avoids introducing SSR complexity that is not needed for this assignment.

The backend will use Python, FastAPI, and Pydantic. That stack gives a clean API surface, strong typing, straightforward request validation, and a natural integration point for an LLM phrasing layer.

SQLite is the right persistence choice for this scope. It keeps local setup friction low while still allowing the data model to be explicit and relational.

---

## 4. Scenarios

The product will support exactly three scenarios.

### Scenario 1: Meal goal mismatch

If a member logs a high-carb meal while their goal is low-carb, the system will suggest a lighter next meal. This is a high-confidence nudge because the rule match is direct and easy to explain.

### Scenario 2: Missed weight logging

If a member has not logged weight for several days, the system will generate a gentle reminder to check in. This usually falls in the medium to high confidence range because the signal is clear but the best phrasing should stay soft.

### Scenario 3: Support risk

If signals indicate low mood combined with repeated dismissals, or if the member explicitly asks for help, the system will escalate the case to a coach. This is the low-confidence path where the product should defer to a human rather than continue automated nudging.

---

## 5. Confidence Policy

Confidence handling should be explicit and predictable.

| Tier   | Range     | Behavior                                                |
| ------ | --------- | ------------------------------------------------------- |
| High   | >= 0.75   | Deliver the nudge immediately                           |
| Medium | 0.50-0.74 | Deliver with softer language and flag in coach view     |
| Low    | < 0.50    | Do not auto-deliver; create escalation for coach review |

This policy gives low-confidence cases a clear destination and makes the coach experience meaningfully tied to the decisioning model.

---

## 6. Decision Engine

The decision engine will use three explicit evaluator functions. This is deliberate: the assignment calls for clear thinking and traceable behavior, not a generic rules framework.

1. `check_meal_goal_mismatch` compares recent meal signals against the member's stated goal.
2. `check_missing_weight_log` evaluates how long it has been since the last weight signal.
3. `check_support_risk` looks for low mood combined with repeated dismissals or other signals that should push the case toward human review.

The selection flow will stay simple and deterministic: evaluate all scenarios, collect matches, apply fatigue and deduplication rules, pick the highest-priority candidate, and then apply the confidence policy.

Fatigue controls will include no duplicate active nudge of the same type, a cooldown window per nudge type, and a daily cap so the product does not become noisy.

---

## 7. LLM Integration

The LLM should be a visible part of the solution, but it must remain carefully bounded.

### Separation of concerns

- The rule engine decides whether a nudge should exist, what type it is, how confident the system is, and whether escalation is recommended.
- The LLM only improves phrasing after that decision has already been made.

This keeps the core product logic deterministic and testable.

### Graceful degradation

- If `OPENAI_API_KEY` is set, the system can use the LLM to generate phrasing.
- If the key is missing, or if the LLM call fails or times out, the backend will fall back to deterministic templates automatically.
- The application must remain fully usable without an API key.

### Guardrails

- The system prompt will disallow diagnoses, medication guidance, and treatment claims.
- Output length will be capped.
- Responses will be validated against a lightweight blacklist before delivery.
- Every LLM outcome will be logged as either `llm_call` or `llm_fallback`.

This demonstrates responsible AI boundaries in a health context without turning the project into an AI-first prototype.

---

## 8. Data Model

The schema will use six focused tables: `members`, `signals`, `nudges`, `nudge_actions`, `escalations`, and `audit_events`.

### `members`

`id`, `name`, `goal_type`, `profile_json`, `created_at`

### `signals`

`id`, `member_id`, `signal_type`, `payload_json`, `created_at`

### `nudges`

`id`, `member_id`, `nudge_type`, `content`, `explanation`, `matched_reason`, `confidence`, `escalation_recommended`, `status`, `generated_by`, `created_at`, `delivered_at`

### `nudge_actions`

`id`, `nudge_id`, `action_type`, `metadata_json`, `created_at`

### `escalations`

`id`, `nudge_id`, `member_id`, `reason`, `source`, `status`, `created_at`, `resolved_at`

### `audit_events`

`id`, `event_type`, `entity_type`, `entity_id`, `payload_json`, `created_at`

This model is small, but it is complete enough to support the member experience, coach workflow, escalation lifecycle, and audit trail without introducing platform-level complexity too early.

---

## 9. APIs

The API surface should stay compact and directly aligned with the product flow.

| Method | Endpoint                           | Purpose                                  |
| ------ | ---------------------------------- | ---------------------------------------- |
| GET    | `/api/members/{member_id}/nudge`   | Get or generate the active nudge         |
| POST   | `/api/nudges/{nudge_id}/action`    | Record act_now, dismiss, or ask_for_help |
| GET    | `/api/coach/nudges`                | Return recent nudges for coach view      |
| GET    | `/api/coach/escalations`           | Return open escalations queue            |
| POST   | `/api/members/{member_id}/signals` | Seed or demo helper                      |

The `ask_for_help` action will automatically create an escalation so that the member path and coach path remain connected.

---

## 10. Member Experience

The member experience should stay simple and trustworthy.

- Show one active nudge card at a time.
- Include a short explanation such as "Why am I seeing this?" so the recommendation feels grounded in member context.
- Offer exactly three actions: Act now, Dismiss, and Ask for help.

The goal is not feature richness. The goal is to make the workflow legible and believable.

---

## 11. Coach Experience

The coach view should make it easy to understand what the system has done and where human intervention is needed.

The recent nudges feed will show member name, nudge type, content, explanation, confidence, user response, escalation flag, and timestamp.

The open escalations queue will show member name, reason, source, status, and timestamp.

Lightweight filters can be added if they are cheap, but they are not required for the core submission.

---

## 12. Logging and Auditability

The system should persist a clear audit trail for the key events in the workflow.

Persisted audit events will include `nudge_generated`, `user_action`, `escalation_created`, `llm_call`, and `llm_fallback`.

Structured backend logs should capture member ID, nudge ID, confidence, matched reason, escalation decision, and whether the final phrasing came from a template or the LLM.

This gives the project a credible safety and observability story without adding heavy operational machinery.

---

## 13. Seed Data

The seed dataset should let a reviewer exercise the core flows immediately.

- One member for the meal mismatch case
- One member for the missed weight logging case
- One member for the support-risk or escalation case
- At least one previously acted nudge and one previously dismissed nudge

That is enough to demonstrate both happy-path behavior and stateful history.

---

## 14. Testing

Testing should focus on the parts of the system that are most important to trust.

### Backend tests

1. Meal mismatch produces the correct nudge candidate.
2. Missing weight log produces the correct reminder.
3. Support risk follows the low-confidence escalation path.
4. No matching signals produces no nudge.
5. Ask-for-help creates an escalation.
6. Active nudge retrieval is idempotent.
7. LLM failure falls back to templates correctly.

### Manual verification

Walk all three scenarios end to end through both the member view and the coach view.

---

## 15. Implementation Order

The work should be sequenced so the core slice is always getting more complete rather than wider.

| Phase                | Steps                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| **Foundation**       | Repo structure, SQLite schema, seed data                                   |
| **Decisioning**      | Evaluator functions, confidence policy, fatigue controls, nudge generation |
| **LLM layer**        | LLM phrasing service, fallback, guardrails, audit logging                  |
| **Member flow**      | Member page, action handling, frontend-to-backend wiring                   |
| **Coach flow**       | Recent nudges view, escalation queue                                       |
| **Quality and docs** | Focused tests, README, product and technical note                          |

This order protects the submission from ending up with UI shells that are not backed by working logic.

---

## 16. Documentation Deliverables

The written deliverables should describe the implemented system clearly and without over-claiming.

`README.md` should include setup instructions, a simple architecture diagram, an explanation of the approach, a two-week improvement plan, and an AI usage disclosure.

The product and technical note should cover the user problem, assumptions, success metrics, major risks, and rollout plan. It should describe the actual system that was built, not a larger future-state architecture.

---

## 17. Intentional Exclusions

This plan intentionally excludes production auth, Docker, PostgreSQL, configurable rules UI, analytics dashboards, multi-channel delivery, coach workload management, real health data, ML confidence models, and compliance-grade infrastructure.

That is a deliberate tradeoff. A strong submission here is a coherent and defensible vertical slice, not a broad but incomplete platform sketch.
