# Software Engineering Best Practices

This document lists and explains the software-engineering practices this repository
aims to follow. It is the "why" behind the rules in [CLAUDE.md](CLAUDE.md); CLAUDE.md
is the operational checklist, this file is the reasoning.

The practices are grouped from the most fundamental (how we structure code) to the
most operational (how we ship it).

---

## 1. Design and architecture

### 1.1 Separation of concerns
Each module should have one reason to change. Keep three responsibilities apart:

- **Orchestration** — control flow, sequencing, "what happens next".
- **Reasoning / business logic** — domain calculations and decisions.
- **Side effects / I/O** — files, network, UI rendering, printing.

When these are mixed in one place, a change to the UI risks breaking a tax
calculation, and the calculation cannot be tested without spinning up the UI.

> In this project this maps to the design doc's rule: *"The NiceGUI layer only calls
> the engine; it does not contain business logic."* Business math (e.g. pension-point
> estimation) belongs in a pure engine module, not in a UI event handler.

### 1.2 High cohesion, low coupling
A unit should do one thing well (cohesion) and depend on as few other units as
possible (coupling). A well-designed component can be **understood, tested, and
replaced in isolation** without reading the rest of the system.

Symptoms of poor cohesion/coupling:
- A single function spanning hundreds of lines that touches many concerns.
- A change in one module rippling unexpectedly through several others.

### 1.3 Small functions and modules
Prefer functions whose entire purpose is obvious from a brief read. Long functions
hide branches, accumulate state, and resist testing. Extract cohesive steps into
named helpers; the names become documentation.

### 1.4 Abstractions earn their place
Introduce an abstraction only when it removes real duplication or hides complexity
the caller should not need to know. A premature or leaky abstraction is worse than
none — it adds indirection without reducing complexity. If you cannot name it
clearly, it is probably the wrong boundary.

### 1.5 Design for change / extensibility
Good code is easy to change. Anticipate the *axes* of likely change and make those
cheap. Examples from this project's design doc:
- New asset types should be addable by implementing a small interface, **not** by
  editing a giant branch inside the monthly loop.
- Tax rules should be pluggable so a different regime can be swapped in.
- Per-month "hook points" let new adjustments slot in without restructuring the loop.

### 1.6 Testability is a design signal
If something is hard to test, that is a **design** problem, not a testing problem.
Hard-to-test code usually signals tight coupling, hidden state, or mixed concerns.
Use the difficulty as a diagnostic and fix the boundary.

---

## 2. Code quality

### 2.1 Type everything
Use type hints on function signatures, public APIs, and meaningful internal
variables. Prefer concrete types; write `Optional[X]` / `X | None` explicitly.
Static typing catches a whole class of bugs before runtime and documents intent.
Enforce it with a type checker (mypy) in CI, not just by convention.

### 2.2 Fail loudly
Do not swallow errors. A bare `except Exception: pass` hides bugs and produces
silent, wrong results — the worst failure mode for a financial forecast. Catch the
**narrowest** exception you can handle, handle it meaningfully, and let everything
else propagate.

### 2.3 No dead or defensive cruft
Remove code that cannot execute or defends against impossible states (e.g.
`getattr(obj, "field", default)` on a dataclass that always has that field). Dead
defensiveness misleads the next reader into thinking the state is possible.

### 2.4 Make illegal states unrepresentable
Prefer enums and typed models over "stringly-typed" values. If a field can only be
`"proportional"`, model it as an enum so the type system — not a runtime string
comparison — enforces validity.

### 2.5 Validate at the boundary
Validate all external input (config files, user input, env vars) once, at the edge,
into typed models. Internal code then trusts its inputs instead of re-checking them.

### 2.6 Clarity over cleverness
Choose the simplest correct solution. Comment **intent** ("why"), not mechanics
("what"); the code already says what it does.

### 2.7 Don't repeat yourself — judiciously
Collapse genuine duplication (e.g. three near-identical parsers differing only by a
prefix). But do not over-DRY unrelated code that merely looks similar today.

---

## 3. Testing

### 3.1 Test behavior, not implementation
Tests should pin down observable behavior so refactors are safe. Cover the expected
path, edge cases, and past regressions.

### 3.2 Mirror the source tree
Unit tests live under `tests/` mirroring `src/` (e.g. `src/finev/forecast.py` →
`tests/finev/test_forecast.py`). A predictable layout makes the test for any module
findable instantly.

### 3.3 TDD where it helps
For new functionality, prefer red-green-refactor: write a failing test, write the
minimum code to pass, then refactor with the test as a safety net.

### 3.4 Coverage is a floor, not a goal
Enforce a minimum coverage so quality cannot silently regress, and ratchet it
upward as coverage improves. But 100% line coverage of trivial code is not the
objective — meaningful behavioral assertions are.

---

## 4. Empiricism over speculation

Treat development as an empirical discipline: **measure, observe, adjust** — don't
guess and proceed.

- Before changing performance or behavior, record a **baseline**.
- Make **one** change at a time so causality is clear.
- Re-measure; if a change did not help (or made things worse), revert it.
- A change you cannot measure is unverified — make it observable first.

This is the basis of the eval-improvement loop in CLAUDE.md: baseline →
hypothesize → change → evaluate → decide, with explicit exit conditions.

---

## 5. Version control and integration

### 5.1 Small, frequent, releasable commits
Integrate with `main` often (at least daily). Keep branches short-lived — a
long-running branch accumulates merge risk. `main` must remain **releasable at all
times**: never merge code that breaks the build, fails tests, or leaves a feature
half-wired without a flag.

### 5.2 Incremental, always-valid steps
If a change is too large to land safely in one go, break it into smaller steps that
each leave the system in a valid, green state. Hide incomplete work behind a flag
rather than keeping it on a branch for weeks.

### 5.3 Conventional commits
`<type>(<scope>): <what and why>` with type in
`feat | fix | chore | docs | refactor | test | ci`. A readable history is a
debugging tool.

---

## 6. Automation and CI

### 6.1 The same checks locally and in CI
What gates a merge in CI should be runnable locally with one command. This project
uses `mise` tasks (`format`, `lint`, `test`, `typecheck`, `coverage`) as the single
source of truth, invoked identically by developers, pre-commit hooks, and CI.

### 6.2 Layered gates
Cheap, fast checks first (format, lint, type), then tests, then coverage. Fail fast
on the cheapest signal.

### 6.3 Reproducibility
Pin tool and language versions (`mise.toml`, `.python-version`) and lock
dependencies (`uv.lock`) so every environment — laptop or CI — resolves to the same
versions. Drift between the pinned and the actually-running version is a bug.

---

## 7. Safety and data handling

- Never commit secrets; use environment variables or a secret store.
- Do not log sensitive data; redact at ingestion boundaries.
- Validate external inputs with typed models before use.
- For unreliable boundaries (network, subprocesses), add timeouts and bounded
  retries, and provide explicit error states — no silent failures.

---

## How this maps to finev

| Practice | Where it shows up here |
|---|---|
| Engine/UI separation (§1.1) | `forecast.py`/`config.py` are pure; `ui.py`/`cli.py`/`app.py` are presentation. Business math must not live in UI handlers. |
| Pluggable rules (§1.5) | ETF/inheritance tax and DRV pension rules are config-driven and should be replaceable components. |
| Validate at boundary (§2.5) | `config.py` parses and validates `config.json` into frozen dataclasses; `forecast.py` validates profile/assets/withdrawal up front. |
| Type checking (§2.1) | `mise run typecheck` (mypy) in CI alongside lint. |
| Mirror tests (§3.2) | `tests/finev/` mirrors `src/finev/`. |
| Reproducibility (§6.3) | Python pinned in `mise.toml` / `.python-version`; deps in `uv.lock`. |
