# Context-Aware Health Nudge

A focused vertical slice demonstrating context-aware health nudging, deterministic decisioning with bounded LLM fallbacks, and a clean member-to-coach escalation flow.

## Quick Start

The project runs locally with or without an `OPENAI_API_KEY`. Without a key, the app gracefully degrades to deterministic templates and conservative meal analysis.

Requires Node.js (≥20) and Python (3.10+).

```bash
# Installs dependencies (Python venv + npm) and seeds the SQLite database
make setup

# Starts frontend (http://localhost:5173) and backend API (http://127.0.0.1:8000)
make dev
```

_(See `.env.example` in `server/` and `client/` for available environment overrides, such as port configurations and timeouts)._

## Deliverables & Documentation

As part of the final delivery, the following core reviewer documents are provided:

- **[Product and Technical Note](docs/product-technical-note.md):** User problem, assumptions, success metrics, and rollout plan.
- **[Manual Verification](docs/manual-verification.md):** Walkthrough checklists for testing the seeded scenarios, live inputs, and structural fallbacks.
- **[Decision Record](docs/plan.md):** The original architectural roadmap, component rationale, and constraints.
- **Implementation Specs:** `docs/phase-01-*.md` through `phase-09-*.md` contain the historical branch-by-branch specifications.

## Demo Reset (Admin Only)

To start fresh during a review session, run the following command while the backend is running (`DEBUG=true` required in `server/.env`):

```bash
curl -X POST http://127.0.0.1:8000/debug/reset-seed
```

This wipes the SQLite database and restores the initial seeded member scenarios, signals, and nudges.

## AI Usage Disclosure

GitHub Copilot was used during development as a pair-programming assistant to help accelerate scaffolding, draft planning documentation, write utility boilerplate, and generate localized React components. All AI-assisted output was reviewed, edited, and validated by a human before being committed.

