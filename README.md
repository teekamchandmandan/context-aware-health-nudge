# Context-Aware Health Nudge

A local prototype for rule-based member nudges, coach escalation, and reviewable decisioning.

## Quick Start

The project runs locally with or without an `OPENAI_API_KEY`. Without a key, the app uses template phrasing and conservative meal-analysis fallbacks.

Requires Node.js (≥20) and Python (3.10+).

```bash
# Installs dependencies (Python venv + npm) and seeds the SQLite database
make setup

# Starts frontend (http://localhost:5173) and backend API (http://127.0.0.1:8000)
make dev
```

After `make dev`, open `http://localhost:5173/member` for the member experience and `http://localhost:5173/coach` for the coach review flow. If Vite chooses a different port because `5173` is already in use, use the frontend URL printed in the terminal.

### Seeded Demo Scenarios

The database is pre-loaded with four members representing distinct states:

| Member           | Signal                                    | Nudge trigger                                                                                                                                              |
| ---------------- | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Alice Chen**   | Logged a pasta-and-bread meal             | Higher-carb meal against a low-carb goal → meal guidance nudge (confidence 0.86)                                                                           |
| **Bob Martinez** | No weight log in 7 days                   | Missing weight log → weight check-in nudge (confidence 0.72)                                                                                               |
| **Carol Davis**  | Logged "low" mood                         | Low mood signal → support escalation nudge (escalation recommended, confidence 0.45). Historical acted and dismissed nudges are visible in the coach view. |
| **Diego Rivera** | Recent weight log, no out-of-range signal | No active nudge — demonstrates the all-good / no-nudge state                                                                                               |

Switch between members using the member switcher in the top-right corner of both views.

Logging a meal, weight, or mood entry in the member view immediately re-evaluates the nudge card, so the seeded scenarios can also be exercised live without a page refresh. If that evaluation produces a new nudge, it supersedes the prior one. Sleep entries are persisted in the same flow, but they are not currently used by the decision engine and therefore do not change the nudge outcome.

_(See `.env.example` in `server/` and `client/` for available environment overrides, such as port configurations and timeouts)._

## Architecture

```mermaid
flowchart TB
    subgraph Client["Client"]
        direction LR
        Mem["Member UI<br/>/member<br/>logging + nudge actions"]
        Cch["Coach UI<br/>/coach<br/>escalation review"]
    end

    API["FastAPI service<br/>member · meal log · nudge action · coach routes"]

    subgraph Engine["Decision Engine"]
        direction LR
        EV["Rule evaluators<br/>meal · weight · support"]
        PO["Selection policy<br/>priority · cooldown · daily cap"]
        PH["Phrasing<br/>template or LLM"]
        MA["Meal photo analysis<br/>classify meal + summary"]
    end

    DB[(SQLite store<br/>members · signals · nudges<br/>actions · escalations · audit)]
    OAI(["OpenAI provider<br/>optional"])

    Mem --> API
    Cch --> API
    API --> EV
    API --> MA
    API --> DB
    EV --> PO --> PH
    PH --> DB
    MA --> DB
    PH -. "if configured" .-> OAI
    MA -. "if configured" .-> OAI

    classDef surface fill:#e0f2fe,stroke:#2563eb,color:#0f172a,stroke-width:1.5px;
    classDef api fill:#dcfce7,stroke:#16a34a,color:#14532d,stroke-width:1.5px;
    classDef runtime fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
    classDef data fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
    classDef external fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-width:1.5px;

    class Mem,Cch surface;
    class API api;
    class EV,PO,PH,MA runtime;
    class DB data;
    class OAI external;

    style Client fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px,color:#0f172a;
    style Engine fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px,color:#0f172a;
    linkStyle default stroke:#334155,stroke-width:2px,fill:none;
```

The core design principle is **rules first, LLM at the edges**. Decisioning — which nudge to surface, at what confidence, whether to escalate — is handled entirely by deterministic rule evaluators and a priority/fatigue policy. This makes every decision auditable and reproducible without a model, and keeps the escalation boundary (a safety concern) outside probabilistic systems. LLM calls are reserved for two bounded, fallback-safe tasks: rewriting pre-approved nudge text into natural language, and classifying a meal photo. Both have template fallbacks and output validation. SQLite was chosen to eliminate infrastructure dependency for a prototype; it can be swapped for PostgreSQL without touching the application layer.

Architecture at a glance:

- **Client** — React 19 + Vite + Tailwind. Two routes: `/member` (nudge card, quick logging) and `/coach` (escalations, recent nudges).
- **API** — FastAPI routers with typed Pydantic request/response models. No business logic lives here.
- **Engine** — Deterministic rule evaluators select a nudge candidate; fatigue policy filters it; optional LLM phrasing rewrites the text (with template fallback). Meal photo analysis is a separate bounded LLM call.
- **Data** — SQLite with 6 tables: `members`, `signals`, `nudges`, `nudge_actions`, `escalations`, `audit_events`. Seeded with 4 demo scenarios.

### LLM Prompts and Evaluation

Two bounded LLM calls exist in the system. Both use `temperature=0.1` for near-deterministic outputs and have template fallbacks, so the system works identically without an API key.

**Nudge phrasing** (`server/app/phrasing/provider.py`)
The model receives a structured payload — nudge type, member goal, matched reason, explanation basis, tone, and character limits — and is instructed to rewrite the approved nudge text without changing the underlying decision, adding new facts, or introducing medical framing. It returns a JSON object with two fields: `content` (member-facing sentence, ≤120 chars) and `explanation` (why the nudge appeared, ≤120 chars). Output is validated against a blocklist of 14 medical/clinical terms (`diagnose`, `medication`, `prescription`, `dose`, `treatment plan`, `doctor`, `clinician`, `therapy`, and others). Any validation failure, timeout, JSON parse error, or missing key falls back to a static template, and `phrasing_source` in the audit log records which path was taken.

**Meal photo classification** (`server/app/meal_analysis/provider.py`)
The model receives only the image — no member context, no written description — and classifies visible food items into one of four profiles: `higher_carb`, `higher_protein`, `balanced`, or `unclear`. It returns a `visible_food_summary` (one factual sentence ≤160 chars describing only visible items, or null). The model is explicitly instructed to return `unclear` when the image is blurry, cropped, or does not support a confident classification. No advice, warnings, or coaching is permitted. The classification is an input signal to the rule engine; the engine makes the final nudge decision.

For the full product rationale, assumptions, success metrics, and rollout plan, see [docs/product-technical-note.md](docs/product-technical-note.md). For a step-by-step reviewer walkthrough of each seeded scenario, see [docs/manual-verification.md](docs/manual-verification.md).

## Resetting the Demo

To restore the original seeded state at any point, run:

```bash
curl -X POST http://127.0.0.1:8000/debug/reset-seed
```

This wipes and re-seeds the SQLite database. Requires the backend to be running with `DEBUG=true` set in `server/.env` (already set by `make setup`).

## What I Would Improve With Two More Weeks

With two more weeks, I would spend less time broadening the demo and more time closing the gap between a strong local prototype and something a care team could pilot with confidence.

- **Authentication, member opt-in, and role-aware access.** The member switcher works for a seeded demo, but the first real step toward a pilot is replacing it with explicit identity, clear member opt-in to proactive nudges, and clear separation between member and coach access.
- **Coach resolution workflow.** The current escalation path proves the system can flag when automation should stop; the missing half is giving coaches a place to resolve a case, leave notes for follow-up, and close the loop operationally.
- **Delivery beyond the open app.** Right now the value of a nudge depends on the member choosing to reopen the app. Adding push, SMS, or an in-app inbox would make the system more useful at the moment a reminder is needed, not just when the demo is visited.
- **Production-grade data layer and deployment.** SQLite was the right call for a zero-dependency prototype, but moving to PostgreSQL and containerising the app are the natural next steps before running this in any shared environment.
- **LLM prompt versioning and observability.** The two bounded LLM calls are still manageable in code, but a pilot would benefit from prompt versioning, tracing, and fallback monitoring so phrasing and meal-analysis changes stay reviewable without widening the model's role in decisioning.
- **Configurable rule engine.** Thresholds, cooldowns, and daily caps are currently set in code. Moving them to a tracked config with change history would let program teams adjust the rules and add new cases — such as sleep consistency or positive reinforcement — without a code deploy.

## AI Usage Disclosure

### Tools Used

- **GitHub Copilot (VS Code + Agent)** — Used for implementation scaffolding, iteration, test drafting, documentation drafts, and PR review passes across the project. Models used through these workflows included GPT-5.4, Claude Opus 4.6, and other available Copilot models.
- **Agent Skills, Vercel React and FastAPI** — Used selectively through Copilot as code-quality and best-practice references during implementation.
- **Google Stitch** — Used for early visual ideation only; the final UI was implemented directly in the codebase.
- **ChatGPT** — Used for early brainstorming on product framing and architecture tradeoffs before implementation.

### What Was Assisted

- Planning documents (`docs/phase-01-*.md` through `docs/phase-09-*.md`, `docs/plan.md`) were drafted or rewritten with AI assistance, then manually reviewed and refined through follow-up prompts.
- Copilot assisted with scaffolding and autocomplete across the FastAPI, Pydantic, React, and Tailwind code; the final implementation was manually reviewed, locally debugged, and refined through additional prompts.
- AI provided substantial assistance with testing, UI design, and documentation (including this README and the product note); each section was manually reviewed and corrected.
- All pull requests received an additional Copilot Agent review pass before merging to `main`.

### Key Decisions I Made

- The rules-first architecture and the decision to keep escalation deterministic.
- The confidence thresholds, cooldown windows, daily caps, and evaluator choices used for the seeded demo scenarios.
- The boundary that LLM usage is limited to phrasing and meal-photo classification, never final nudge decisioning.
