# Barista Agent — CLAUDE.md

## Project layout

- Application/business logic: `src/barista/`
- Agentic projects (isolated): `.agents/<subproject>/` — each with its own `pyproject.toml`, `mise.toml`, and `src/` tree
- Tests: `tests/`
- Project metadata and tool config: `pyproject.toml`, `mise.toml`

## Python and tooling

- Python 3.12
- Dependency management via `mise run sync` (uv)
- Use `mise` tasks for all common operations:

| Task | Purpose |
|------|---------|
| `mise run sync` | Install / update dependencies |
| `mise run format` | Auto-format code |
| `mise run lint` | Run linter |
| `mise run test` | Run test suite |

- Add a unique `mise` task for every new runnable workflow: `mise run workflow-<slug>`

## General principles

- Make minimal, targeted edits; do not disturb unrelated code
- Keep public APIs stable unless a change is explicitly requested
- Apply separation of concerns — keep orchestration, reasoning, and side effects distinct (see WAT below)
- Fail loudly: do not swallow errors or hide failures
- Leave touched code clearer or safer than you found it, within the task scope

## Empiricism over speculation

- Treat software development as an empirical discipline: measure, observe, adjust — do not guess and proceed
- When facing a design decision or a performance question, prefer a small focused experiment over a confident assumption
- If you cannot measure whether a change improved things, treat the change as unverified — find a way to make it observable before committing to it
- This applies to agentic work especially: a hypothesis about prompt behavior or tool performance is only valid after evaluation, not before

## Design

### Modularity

- Design every module, class, and tool for high cohesion and low coupling — each unit should do one thing well and depend on as few others as possible
- A component is well-designed if it can be understood, tested, and replaced in isolation without understanding the rest of the system
- Avoid deep dependency chains; if a change in one module ripples unexpectedly through others, treat that as a design problem to fix, not a fact to work around
- Keep modules small enough that their entire purpose is obvious from a brief read

### Abstractions

- Introduce an abstraction only when it removes genuine duplication or hides a complexity that callers should not need to know about
- A leaky or premature abstraction is worse than no abstraction — it adds indirection without reducing complexity
- If an abstraction is hard to name clearly, it is probably the wrong boundary; reconsider the split
- When removing or collapsing an abstraction makes the code clearer, do it — more layers are not inherently better

### Testability as a design signal

- If something is hard to test, that is a design problem, not a testing problem — fix the design
- Hard-to-test code is typically a symptom of tight coupling, hidden state, or mixed concerns; use the difficulty as a diagnostic
- Design modules and tools so their behavior can be verified without running the full system; if you need the whole stack to test one function, the boundaries are wrong

## Code style

- Use type hints throughout: function signatures, public APIs, and meaningful internal variables
- Prefer concrete types; use `Optional`/`Union` explicitly rather than implicitly
- Write Google-style docstrings for every public function, method, and class
- Prefer clarity over cleverness — choose the simplest correct solution
- Comment only when logic is non-obvious; document intent, not mechanics

## Testing

These rules apply to correctness tests (unit, integration, replay). For benchmarking and optimization loops, see the next section.

- Use `pytest` (not `unittest`)
- Tests live in `tests/`; mirror the source tree for unit tests:
  - `tests/agents/` — agent behavior tests with mocked tools/models
  - `tests/tools/` — deterministic tool unit tests
  - `tests/workflows/` — workflow integration and replay tests
- Follow TDD for new functionality:
  1. Write failing tests first
  2. Implement the minimum code to pass
  3. Refactor while keeping tests green
- Keep tests small, focused on behavior, and free of unnecessary duplication
- Cover: expected behavior, edge cases, and regressions
- Every new agentic feature requires:
  - Unit tests for tools and guardrails
  - Integration tests for workflow paths and failure cases
  - At least one determinism/replay test for non-trivial workflows

## Eval-improvement loop (benchmarking and optimization)

When improving code quality, performance, or model behavior, run a structured improvement loop rather than making ad-hoc changes.

**Loop structure**
1. **Baseline** — run the benchmark or eval suite and record the current score/metric
2. **Hypothesize** — identify the most likely lever for improvement based on the results
3. **Change** — make one focused change (prompt, logic, model, config, etc.)
4. **Evaluate** — re-run the benchmark and compare against the previous score
5. **Decide** — continue if there is meaningful improvement; stop if the exit condition is met

**Exit conditions — stop the loop when any of the following is true**
- The target metric or goal has been reached
- The last N consecutive cycles produced improvement below the minimum threshold (default: N=3 cycles, threshold=1%)
- A hard cycle cap is reached (default: 10 cycles) — log a summary and stop rather than running indefinitely

**Rules**
- Make only one change per cycle so causality is clear; do not bundle multiple changes
- Record every cycle: what changed, what the score was before and after, and why the change was made
- If a change makes things worse, revert it before the next cycle
- If the loop exits without reaching the goal, summarize what was tried, what the ceiling appears to be, and what the next logical avenue would be
- Never silently exit the loop — always emit a final summary with the trajectory of scores

## Pre-commit checklist

Work in two loops before committing:

**Loop 1 — formatting and lint (repeat until clean)**
```
mise run format && mise run lint
```
Fix all reported issues, then re-run. Repeat until both pass with no warnings or errors.

**Loop 2 — tests (repeat until green)**
```
mise run test
```
Fix all failures, then re-run. Repeat until the full suite passes.

Do not move from loop 1 to loop 2 while lint is still failing. Do not commit while any test is failing.

Commit message format: `<type>(<scope>): <concise description of what and why>`

Types: `feat` | `fix` | `chore` | `docs` | `refactor` | `test` | `ci`

Example: `feat(barista): add retry backoff to espresso tool`

## Continuous integration discipline

- Integrate with the mainline branch frequently — at minimum daily, ideally every completed unit of work
- Keep branches short-lived; a branch that lives longer than a day is a liability accumulating merge risk
- `main` must remain releasable at all times — do not merge code that breaks the build, fails tests, or leaves a feature half-wired without a flag
- Use feature flags to merge incomplete work safely rather than keeping long-running branches
- If a change is too large to integrate safely in one go, break it into smaller steps that each leave the system in a valid state

## Deployability

- Every commit merged to `main` should be releasable — not necessarily released, but ready to be
- Incomplete features must be hidden behind a flag or left fully inactive, not left partially wired
- Treat a broken `main` as the highest priority fix; nothing else takes precedence until it is green

## Security and data handling

- Never commit secrets or credentials; use environment variables or a secret store
- Avoid logging sensitive data; redact or omit at ingestion boundaries
- Validate all external inputs with Pydantic models before use

## Agentic AI — WAT pattern

All agentic features follow the **WAT** separation strictly:

| Layer | Responsibility |
|-------|---------------|
| **W**orkflow | Orchestration and control flow only — no reasoning, no side effects |
| **A**gent | Reasoning and decision logic only — no direct I/O or tool calls outside the framework |
| **T**ool | Deterministic capabilities and side effects only — no reasoning |

**Prompts must not encode workflow routing, retries, or policy decisions.** Keep orchestration in the workflow layer.

Use **PydanticAI** for agent/model integration and structured outputs by default. If graph orchestration is needed, LangGraph may be used as the workflow engine while preserving WAT separation.

## Agentic AI — folder conventions

```
.agents/
  tools/        # standalone tool implementations and integrations
  workflows/    # standalone workflow orchestration and checkpoints
  agents/       # standalone agent definitions and prompts
  schemas/      # shared Pydantic models across agentic projects
  guardrails/   # safety policies, budgets, and validation
```

Each subdirectory under `.agents/` is an isolated Python project with its own `pyproject.toml`, `mise.toml`, and `src/` tree. Do **not** add agentic dependencies to the main `pyproject.toml`.

## Agentic AI — new workflow checklist

For every new workflow `<workflow_slug>`, create these docs before writing code:

| File | Contents |
|------|---------|
| `docs/workflows/<slug>/specification.md` | Problem statement, stakeholders, SHALL requirements, non-goals, acceptance criteria |
| `docs/workflows/<slug>/plan.md` | Scope, architecture and WAT mapping, milestones, test strategy, rollout |
| `docs/workflows/<slug>/README.md` | Purpose, inputs/outputs, architecture, running, configuration, testing, limitations |

If requirements are unclear, ask before implementing.

When modifying an existing workflow, update only that workflow's scoped docs.

## Agentic AI — determinism, safety, and robustness

**Determinism**
- Use typed Pydantic models for all workflow state
- Make workflow transitions explicit and replayable
- Use stable serialization and hashable checkpoints for replay tests

**Safety**
- Enforce tool allowlists/denylists per environment
- Validate all tool inputs and outputs with Pydantic models
- Add timeouts, retries with bounded counts and exponential backoff

**Robustness**
- Fail closed on policy validation errors
- Treat tools as unreliable boundaries; handle transient failures explicitly
- Provide fallback paths and explicit error states — no silent failures

**Cost efficiency**
- Prefer cheaper models where output quality is acceptable; escalate deliberately
- Cache responses where deterministic and safe
- Track token/cost budgets in workflows and enforce hard caps
