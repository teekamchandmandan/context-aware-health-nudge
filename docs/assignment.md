# Digbi Health Product Engineering Assignment

## Overview

This assignment is designed to assess how you reason across product experience, system design, platform extensibility, and end-to-end execution. We care more about thoughtful decisions, clear tradeoffs, and strong structure than visual polish.

## Context

Digbi Health is building proactive, context-aware care experiences that help members make the right health actions at the right time. For this exercise, you will design and implement a small but meaningful vertical slice of that experience.

## Problem Statement

Context-aware nudges can improve engagement and compliance when the system understands the member’s context, needs, recent signals, and responds with the right action at the right time.

Build a feature called **Context-Aware Health Nudge** that uses member context to generate a personalised nudge, explain why the user is seeing it, and support safe escalation when the system should defer to a human.

### Example Scenarios

- A member logs a meal that is inconsistent with their goals, and the system suggests a better next step for dinner.
- A member has not logged weight in several days, and the system prompts a quick check-in.
- Recent activity suggests the user may need active care support.

## What to Build

1. A member-facing experience that shows a personalised nudge, explains why it appeared, and offers three actions: act now, dismiss, or ask for help.
2. A clear data model for users, signals/events, nudges, user actions, confidence, and audit history.
3. A backend service with APIs to fetch user context, generate or return a nudge, and store nudge history and user actions.
4. A lightweight decision engine using rules, heuristics, or an LLM-backed approach. Low-confidence cases should be handled explicitly.
5. A basic internal page or coach view that shows recent nudges, the reason each was generated, confidence or rule matched, user response, and whether escalation is recommended.
6. Logging that captures the key events needed to measure product performance, quality, and safety.

## Key Points to Consider

### Scope

Build a small end-to-end vertical slice rather than a broad platform mockup.

### Data

Use mocked or simulated data with an LLM; do not connect to real health data sources. Digbi will not be providing any data sources for this assignment.

### Auth

Authentication is not required.

### Language

You may use any framework or language. Choose what best helps you communicate your thinking.

### Tradeoffs

Optimise for thoughtful structure and decision-making rather than pixel-perfect polish.

### AI Tools

Using AI-powered IDEs or coding assistants is acceptable, as these are commonly used in real-world environments, and this assignment is intended to reflect that. If you’ve used AI tools to help you write code or docs, or any other part of your process, we ask that you disclose how and where you used them.

This isn’t to catch you out. It’s an opportunity to demonstrate that you understand how to use these tools effectively and responsibly in your workflow.

## Required Deliverables

1. Source code for the working prototype (preferably as a GitHub repo).
2. A `README` with the following:
   - Set up instructions.
   - A simple architecture diagram or system sketch and a quick explanation of the approach.
   - A short section describing what you would improve if you had two additional weeks.
   - If any AI is used as part of the assignment, a short note declaring which tools you used and how you used them.
3. A 1–2 page product and technical note covering the user problem, assumptions, success metrics, major risks, and rollout plan.

## Submission Instructions

- Submit a repository link or a ZIP file containing your work.
- Make sure the `README` explains how to run the project locally.
- If you choose to use AI features, be explicit about prompts and evaluation logic.
- If time runs short, prioritise a coherent end-to-end slice and document what you intentionally left out.

## What We Will Look For

- **Product judgment:** Does the solution solve a meaningful member problem in a clear and trustworthy way?
- **Systems thinking:** Are signals, decision-making, delivery, and logging cleanly separated?
- **Platform thinking:** Could the design support additional nudge types or channels without a major rewrite?
- **Full-stack execution:** Does the UI, API, data model, and internal view connect coherently?
- **Communication:** Are assumptions, tradeoffs, and next steps explained clearly?

## Final Note

We are not judging production polish. We are judging how you frame problems, make decisions, balance product and engineering tradeoffs, and communicate clearly.

There is no single correct implementation. We are interested in how you think and what you prioritise. A thoughtful, scoped solution is stronger than a broad but shallow one.

Please ask clarifying questions only if something is genuinely blocking. Otherwise, make reasonable assumptions and move forward.
