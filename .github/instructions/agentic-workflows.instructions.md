---
applyTo: "src/barista/**/*.py,tests/**/*.py"
description: "Use when creating or modifying agentic workflows, agents, tools, guardrails, or workflow schemas. Enforces PydanticAI + WAT architecture with determinism, safety, robustness, and cost controls."
---

# Agentic Workflow Generation Rules

## Process requirements (required)
- For repositories with multiple workflows, keep workflow docs scoped per workflow to avoid collisions.
- For each new workflow `<workflow_slug>`, create or update `docs/workflows/<workflow_slug>/specification.md`.
- In each workflow's `specification.md`, write product-stakeholder requirements using explicit SHALL language.
- After `specification.md`, create or update `docs/workflows/<workflow_slug>/plan.md` with a concrete implementation plan.
- If any requirement is ambiguous or missing, ask the user for clarification before implementation.
- For each workflow, add a comprehensive README at `docs/workflows/<workflow_slug>/README.md` that explains purpose, architecture, execution, inputs/outputs, and testing.
- For each new runnable workflow, add a corresponding unique `mise` task in `mise.toml` (for example `workflow-<workflow_slug>`).
- When modifying an existing workflow, update only that workflow's scoped docs (`specification.md`, `plan.md`, `README.md`).

## Workflow docs template (required)
- Workflow docs root SHALL be `docs/workflows/<workflow_slug>/`.
- `specification.md` SHALL contain these sections in order:
	- `# Specification: <Workflow Name>`
	- `## Problem Statement`
	- `## Stakeholders`
	- `## Requirements (SHALL)`
	- `## Non-Goals`
	- `## Acceptance Criteria`
- `plan.md` SHALL contain these sections in order:
	- `# Implementation Plan: <Workflow Name>`
	- `## Scope`
	- `## Architecture and WAT Mapping`
	- `## Milestones`
	- `## Test Strategy`
	- `## Rollout and Validation`
- `README.md` SHALL contain these sections in order:
	- `# <Workflow Name>`
	- `## Purpose`
	- `## Inputs and Outputs`
	- `## Architecture`
	- `## Running`
	- `## Configuration`
	- `## Testing`
	- `## Limitations`

## Stack defaults
- Default to Python + PydanticAI for agentic workflow implementation.
- Keep model provider usage behind typed interfaces to avoid lock-in.
- Prefer deterministic execution paths over purely conversational loops.

## WAT separation (required)
- Workflows layer (`src/barista/workflows/`): orchestration only (routing, retries, checkpoints, state transitions).
- Agents layer (`src/barista/agents/`): reasoning and planning only.
- Tools layer (`src/barista/tools/`): deterministic side effects and external integrations.
- Do not mix orchestration logic into prompts or tools.

## Required structure for new features
- `src/barista/workflows/`
- `src/barista/agents/`
- `src/barista/tools/`
- `src/barista/schemas/`
- `src/barista/guardrails/`
- `tests/workflows/`
- `tests/agents/`
- `tests/tools/`

## Determinism requirements
- Use typed workflow state models (Pydantic).
- Make transitions explicit, replayable, and testable.
- Use stable serialization for checkpoints and event logs.
- Add at least one replay test for non-trivial workflows.

## Safety, robustness, and failure tolerance requirements
- Validate all tool inputs/outputs using Pydantic schemas.
- Enforce environment-specific tool policies (allowlist/denylist).
- Add timeout bounds and bounded retries with backoff for tool calls.
- Fail closed on policy or validation errors.
- Add explicit fallback/error branches instead of silent failure.

## Cost efficiency requirements
- Track token/cost budget in workflow state.
- Enforce hard budget caps.
- Prefer cheap models for low-risk steps and escalate only when needed.
- Cache deterministic model/tool results when safe.

## Testing requirements
- Add unit tests for tools and guardrails.
- Add integration tests for workflow paths and failure paths.
- Keep tests focused, deterministic, and readable.
