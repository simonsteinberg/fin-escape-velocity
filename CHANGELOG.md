# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See [docs/VERSIONING.md](docs/VERSIONING.md) for how releases are cut and how a
version is retired.

## [Unreleased]

### Added

- Versioning system: SemVer source of truth in `pyproject.toml`, a maintained
  changelog, the in-app version label, and the `mise run release` workflow.

### Changed

- Renamed the app title and page header from "Wealth Forecast" to "Financial
  Escape Velocity - Wealth Forecast" (#22).

## [0.1.0] - 2026-06-06

### Added

- Initial baseline release of the German personal-finance forecasting tool: a
  NiceGUI web app and CLI that projects wealth over time, accounting for ETF
  gains, bAV (occupational pension) transfers/payouts, DRV state pension,
  inheritance (Erbschaftsteuer), and German-specific taxation (Abgeltungssteuer
  and Soli).

[Unreleased]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/simonsteinberg/fin-escape-velocity/releases/tag/v0.1.0
