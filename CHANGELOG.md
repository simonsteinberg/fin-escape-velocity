# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See [docs/VERSIONING.md](docs/VERSIONING.md) for how releases are cut and how a
version is retired.

## [Unreleased]

### Added

- **Language toggle (English/German):** an always-visible navbar control switches
  the entire UI between English (default) and German. All user-facing text is
  resolved through a new pure `finev.i18n` translation catalog (English→key
  fallback); the chosen language is persisted in the autosave cache and restored
  on reload. Currency/number formatting is not localized in this iteration (#33).
- New **VBLklassik** asset type: the public-sector occupational pension modeled
  as a lifelong, income-taxed annuity that offsets post-retirement withdrawals
  (like the DRV state pension, but nominal — not inflation-compensated). Entered
  as Versorgungspunkte (× €4/point) or a direct gross monthly euro amount, with a
  "still in public service" checkbox that accrues one point per working year. Adds
  `VBL_RENTE_PRO_PUNKT_EURO` and `VBL_BRUTTO_RENTE_STEUERSATZ` config keys.
- Versioning system: SemVer source of truth in `pyproject.toml`, a maintained
  changelog, the in-app version label, and the `mise run release` workflow.
- App favicon: a modern, scalable SVG icon (a rising-trend arrow) bundled as a
  package asset and served as the browser tab icon.
- Top navbar: an always-visible header carrying the logo and title, a **File**
  action that opens the save/load/delete profile window, and an **About** action
  that shows the current version (#26).
- Navbar **Export** action: downloads the detailed monthly forecast (every month
  and every backend-computed column) as a timestamped CSV via the browser's
  download folder, with EURO values rounded to whole-euro integers to keep the
  file frugal (#28).

### Changed

- Renamed the app title and page header from "Wealth Forecast" to "Financial
  Escape Velocity - Wealth Forecast" (#22).
- Navbar polish: the logo is rescaled to fit the header height (it no longer
  overflows), the File/About actions are left-aligned next to the title, and the
  header background is a teal that matches the logo's colours.

## [0.1.0] - 2026-06-06

### Added

- Initial baseline release of the German personal-finance forecasting tool: a
  NiceGUI web app and CLI that projects wealth over time, accounting for ETF
  gains, bAV (occupational pension) transfers/payouts, DRV state pension,
  inheritance (Erbschaftsteuer), and German-specific taxation (Abgeltungssteuer
  and Soli).

[Unreleased]: https://github.com/simonsteinberg/fin-escape-velocity/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/simonsteinberg/fin-escape-velocity/releases/tag/v0.1.0
