# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See [docs/VERSIONING.md](docs/VERSIONING.md) for how releases are cut and how a
version is retired.

## [Unreleased]

### Added

- "Average annual salary increase (%)" input in the State pension panel
  (0.1% steps, default 0.5%). Pension points are earned in proportion to each
  year's salary, so the accrued pension now compounds with the raise instead of
  crediting every working year the same amount. The engine and the read-only
  "Pension at age X" line share one formula
  (`pension.accrued_pension_growth`), so they can no longer disagree.

### Changed

- The default example now starts with 350 EUR/month of state pension already
  earned and a 40,000 EUR annual income (was 0 EUR and 50,000 EUR).

### Fixed

- The Notgroschen retirement top-up no longer counts as spending. It is drawn
  from the other assets on top of the monthly withdrawal (unchanged, and it can
  still trigger ETF capital-gains tax), but the money stays in the portfolio,
  so "Net Cashflow p.m." reported it as an outflow it never was: a 1,000 EUR
  withdrawal with a 24.77 EUR top-up read as -1,024.77 instead of -1,000.

## [0.5.1] - 2026-08-09

### Changed

- New default scenario in both the web app and the CLI: a 30-year-old (was 40)
  with a 100,000 EUR ETF savings plan at 500 EUR/month, a 15,000 EUR
  Notgroschen, a 100,000 EUR inheritance at age 70, and a 50,000 EUR car
  purchase at age 40. The old bAV and plain daily-account rows are gone from
  the defaults, so the starting example now shows one of every kind of entry.
  Saved profiles and any existing autosaved state are untouched.

### Fixed

- Chart and data table now sample the forecast on birthdays instead of every
  twelfth month from the forecast start. With a current age of, say, 25 years
  and 1 month, the row labelled "26" held the balance at 26 years and 1 month
  (12 monthly contributions), so changing the start month left every displayed
  value unchanged. It now shows the balance at exactly 26 years and 0 months
  (11 contributions). The forecast engine itself was already correct; only the
  yearly display sampling was off.

## [0.5.0] - 2026-08-09

### Added

- Cash assets can be marked as a **Notgroschen** (emergency fund): a protected
  buffer the forecast never withdraws from and never allocates into, so it
  survives even when the other assets are exhausted and the withdrawal turns
  into debt. Before retirement it takes contributions like any Cash account.
  A second tick box chooses what happens in retirement: leave the buffer alone,
  or keep its inflation adaption at a user-defined annual rate (0.1% steps),
  topped up monthly from the other assets and skipped in any month they cannot
  cover it. The buffer's role in a bear market (spending cash instead of
  selling ETFs) is deliberately not simulated; only its existence and upkeep
  are.

- New `Investment` asset type for planned purchases, in two modes. A *one-time
  purchase* (e.g. a car at age 55) is paid out of the assets in that month; a
  *financed purchase* (e.g. a house on a mortgage) takes on a loan at a given
  annual interest rate and repays it with a fixed monthly amount until it
  reaches zero. Purchases and repayments are raised from the assets exactly
  like a withdrawal (ETF capital-gains tax and borrowing included), and an
  outstanding loan reduces total wealth, so financing costs show up as the
  interest paid. Loan terms that never repay the loan (a payment at or below
  the first month's interest) are rejected with an explanatory error. What is
  bought is not tracked as wealth.

- Per-asset annual contribution adaption: every asset with a monthly
  contribution (ETF, bAV and Cash alike, so the daily account can now save a
  monthly amount too) gained an "Annual contribution change (%)" input in 0.1%
  steps, default 0%. The contribution steps up (or down, for a negative rate)
  on each anniversary of the forecast start, and is floored at zero so a
  pre-retirement contribution never turns into a withdrawal. Rates at or below
  -100% are rejected by the engine and clamped in the UI.

### Fixed

- Release script (`mise run release`) now strips ANSI color codes from the
  captured `uv version` output. Under `mise` (which forces color) the codes
  leaked into the git tag name, which git rejected, and into the changelog
  headers.

## [0.4.2] - 2026-06-28

### Fixed

- Clicking a spinner arrow (increment/decrement button) on a number input now
  refreshes the chart and data table immediately, without requiring an extra
  Enter keypress or tab away.

## [0.4.1] - 2026-06-18

### Added

- End-to-end tests (`tests/finev/test_e2e.py`, `mise run test-e2e`) that launch
  the two runnable entry points as real subprocesses — `python -m finev.cli`
  (mirroring `mise run run`) and `python -m finev.app` (mirroring `mise run app`)
  — asserting the CLI prints the forecast and the app server boots and serves the
  page.

### Fixed

- Editing a text or number input no longer "throws" the cursor out of the field.
  The live per-keystroke auto-refresh re-rendered the inputs while typing, which
  destroyed and recreated the widget being edited and stole focus. Text/number
  inputs now commit on **Enter or blur** (leaving the field); non-text controls
  (dropdowns, checkboxes, add/remove/reset) still update instantly. The old
  ~0.5s keystroke debounce is removed, since commits are now discrete events.

## [0.4.0] - 2026-06-13

### Added

- New **"Rentenanpassung p.a."** (annual pension adjustment) input in the State
  pension panel, defaulting to 1%. The state pension now grows at this rate over
  time independently of price inflation, instead of automatically tracking the
  inflation rate. When the adjustment rate is below inflation (e.g. 1% vs. 2%),
  the pension grows slower than the inflation-indexed withdrawal target, so its
  real value erodes — the realistic outcome for the German statutory pension.

### Changed

- Redesigned the app favicon/logo from the abstract growth-chart arrow to a
  detailed rocket on a starfield (the "escape velocity" motif).
- The state pension is no longer indexed to the inflation rate. Existing
  scenarios with inflation above 1% will show a lower real state pension than
  before, reflecting the new 1% default adjustment rate.

## [0.3.0] - 2026-06-13

### Added

- A single `?` help icon in each input panel header (Profile, State pension,
  Assets). Hovering it shows a concise read-me for that panel's parameters, in
  both English and German, after a 1.5 s deliberate-pause delay. The help box
  wraps at 40 character widths and uses a slightly larger (16px) font for
  readability. This replaces the per-field hover tooltips (which also fixed a
  duplicate-tooltip bug on some number inputs).

### Changed

- Default ETF annual gain rate raised from 5.0% to 6.0%. Only new ETF rows pick
  up the new default; saved profiles keep their stored rate.

### Removed

- The "e.g. wife" placeholder on the Profile name field (File window); the field
  is now empty until typed.

## [0.2.0] - 2026-06-13

### Added

- Chart toggle to switch the capital (y) axis between linear and logarithmic
  scale. The choice is persisted across reloads alongside the other UI
  preferences. In log view the axis bottom stays at 1000 €, while series values
  are clamped to a 1 € minimum so the log axis stays well-defined for
  non-positive values — a falling series descends past 1000 € and slides off the
  bottom of the chart on its own.

## [0.1.4] - 2026-06-12

### Fixed

- State (DRV) and VBLklassik pensions drawn while still working (start age before
  retirement age) are no longer dropped: in those gap months the combined net
  pension is invested in the highest-gain-rate ETF (or the highest-rate Cash asset
  when no ETF exists). From retirement onward they still offset the withdrawal
  target, so they are never counted twice.
- Working-year pension growth now accrues progressively (capped at retirement)
  instead of crediting the full to-retirement amount up front. A pension that
  starts before retirement no longer overstates its value during the gap years.

## [0.1.3] - 2026-06-09

### Changed

- Trim the README quickstart: drop the standalone "Run a console forecast"
  (`mise run run`) snippet, leaving the NiceGUI app as the primary entry point.

## [0.1.2] - 2026-06-09

### Added

- UI configuration file (`src/finev/ui_config.json`) and loader
  (`finev.ui_config`) for presentation-only settings: `MAX_WIDTH_PX` caps and
  centres the page content width (`0` = full width), and `COLOR_SCHEME`
  (`auto` | `light` | `dark`) selects the default color scheme. `auto` follows
  the operating system / browser `prefers-color-scheme` preference via
  `ui.dark_mode`.
- Navbar color-scheme toggle that cycles `auto → light → dark` live and persists
  the choice to the cached state (alongside the language).
- Theme CSS (`ui_view.theme_css`) so the navbar background, page/card surfaces
  and scrollbars follow the active scheme (keyed on Quasar's `body--dark`
  class), with a neutral-gray dark palette replacing Quasar's near-black
  defaults: a darker page behind clearly lighter mid-gray cards and data table.

## [0.1.1] - 2026-06-06

### Changed

- Sync `CLAUDE.md` with the current codebase: document the `i18n`,
  `profile_store`, and `greet` modules in the architecture table, and add the
  `coverage-ci`, `setup-repo`, and `branch-clean-up` mise tasks to the task table.
- Ignore Claude Code local settings and runtime state (`.claude/settings.local.json`,
  `.claude/scheduled_tasks.lock`).

## [0.1.0] - 2026-06-06

### Added

- Initial baseline release of the German personal-finance forecasting tool: a
  NiceGUI web app and CLI that projects wealth over time, accounting for ETF
  gains, bAV (occupational pension) transfers/payouts, DRV state pension,
  inheritance (Erbschaftsteuer), and German-specific taxation (Abgeltungssteuer
  and Soli).

[Unreleased]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/simonsteinberg/fin-escape-velocity/releases/tag/v0.1.0
