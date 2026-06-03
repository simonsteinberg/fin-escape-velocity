# Code Quality Improvement Plan

A staged plan to bring the codebase in line with [SOFTWARE_ENGINEERING.md](../SOFTWARE_ENGINEERING.md)
and the project's own design doc (`.planning/DESIGN_AND_REQUIREMENTS.md`).

Each stage must leave `main` green (format, lint, typecheck, tests) and releasable.

## Baseline (recorded before changes)

- 65 tests pass; lint clean.
- Coverage 56% overall, but `cli.py` 0%, `ui.py` 21% (the 885-line `build_wealth_page`
  is effectively untested).
- mypy: 2 errors (both trivial `Any | None` coercions in `ui.py`).
- Python version drift: `.python-version` was 3.14 while `mise.toml` pins 3.12.

## Findings

| # | Issue | Principle |
|---|---|---|
| 1 | `ui.py::build_wealth_page` is ~885 lines mixing state persistence, coercion, validation, layout, business logic, forecasting orchestration, and charting | SoC, small functions, testability |
| 2 | DRV pension-point / penalty math lives **inside the UI** event handler | Design doc: "UI only calls the engine" |
| 3 | `forecast_wealth` is a ~370-line function with a ~270-line monthly loop | Extensibility (pluggable asset types / per-month hooks), testability |
| 4 | `except Exception: pass` in `ui.py` | Fail loudly |
| 5 | `getattr(asset, "active", True)` repeated on a frozen dataclass that always has `active` | Dead/defensive cruft |
| 6 | Stringly-typed `WithdrawalPlan.allocation_strategy` and `compute_tax(relationship: str)` | Make illegal states unrepresentable |
| 7 | Tests in `tests/finescape/` plus stray `tests/test_greet.py`; do not mirror `src/finev/` | Mirror the source tree |
| 8 | No type-check or format-check gate in CI / pre-commit | Layered CI gates |
| 9 | Three near-identical `_parse_klasse_*_brackets` parsers | DRY |
| 10 | Python version drift; low coverage floor (40%); `cli.py` untested | Reproducibility, coverage floor |

## Stage 1 — Tooling and hygiene (DONE)

- Align `.python-version` to 3.12 (matches `mise.toml` / `pyproject`).
- Extend ruff lint rules: `I` (imports), `B` (bugbear), `UP` (pyupgrade), `SIM`,
  `RUF`. (Left `E501` to the formatter to avoid noise on long strings.)
- Add mypy as a dev dependency with `[tool.mypy]` config and a `mise run typecheck` task.
- Add `mise run format-check` (`ruff format --check`) and a `mise run check` aggregate.
- Wire `format-check` + `typecheck` into CI and pre-commit.
- Raise the coverage floor to lock in current coverage.

## Stage 2 — Domain purity and small fixes (DONE)

- Extract DRV pension math from `ui.py` into a pure, tested module
  (`src/finev/pension.py`); the UI calls it (fixes #2).
- Remove the `except Exception: pass` (fixes #4).
- Replace `getattr(asset, "active", True)` with `asset.active` (fixes #5).
- Introduce `AllocationStrategy` enum for `WithdrawalPlan.allocation_strategy` (part of #6).
- Collapse the three bracket parsers into one prefix-parameterised helper (fixes #9).
- Move tests to `tests/finev/` mirroring the source; add `cli.py` and `pension.py`
  tests (fixes #7, raises coverage).

## Stage 3 — Decompose `forecast_wealth` (DONE)

Goal: turn the monolithic monthly loop into a small set of cohesive, individually
testable steps so new asset types and per-month adjustments slot in without editing
the loop body (design-doc extensibility).

Proposed shape:
- A `MonthContext` value object (ages, balances, cost bases, config, flags).
- Pure step functions: `apply_inheritance`, `apply_contributions`,
  `apply_withdrawal`, `apply_bav_transfer`, `apply_bav_income`, `apply_growth` —
  each takes and returns the evolving per-month state.
- The loop becomes an ordered pipeline of these steps.
- Per-asset-type behaviour moves behind a small strategy interface so adding an
  asset type means adding a handler, not editing branches.

Each step is extracted one at a time, with the existing forecast tests as the
regression net; behavior must stay identical (verify with a golden-output test).

## Stage 4 — Decompose `build_wealth_page` (PARTIALLY DONE)

Goal: separate UI concerns currently fused in one ~885-line closure.

Done:
- `ui_state.py` — defaults, JSON persistence, coercion, row normalization, and
  row→`Asset` conversion (pure, no NiceGUI; covered by `test_ui.py`).
- `ui_view.py` — currency formatting, chart options, yearly display frame (pure).
- `ui.py` now imports those helpers; the pure logic no longer lives alongside the
  rendering closure. ui.py dropped from 1371 to ~930 lines (the remainder is the
  `build_wealth_page` closure, not yet split).

Verified with a live smoke test: `mise run app` (here, a backgrounded launch +
`curl /`) returns HTTP 200 and renders the full form server-side for both the
default and cached-state paths.

Remaining (still PLANNED): split the closure itself into form-builder and
controller layers so the event handlers become independently testable. This needs
interactive verification per extraction and is deferred to keep each step safe.

## Stage 5 — Finish type-safety pass (DONE)

- `compute_tax` now takes `InheritanceRelationship` (enum-keyed map); `forecast.py`
  carries the enum through `inheritance_events`. StrEnum keeps the string-keyed
  config tests valid.
- `greet.py` uses `importlib.metadata.version("finev")` with a fallback, replacing
  the fragile `parents[2]` lookup.

## Exit criteria

- All stages keep CI green (format, lint, typecheck, tests, coverage floor).
- `ui.py` contains no business math; `forecast_wealth` is a readable pipeline.
- Adding a new asset type touches a handler + tests, not the loop body.
