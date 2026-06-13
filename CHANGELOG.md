# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See [docs/VERSIONING.md](docs/VERSIONING.md) for how releases are cut and how a
version is retired.

## [Unreleased]

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

[Unreleased]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/simonsteinberg/fin-escape-velocity/releases/tag/v0.1.0
